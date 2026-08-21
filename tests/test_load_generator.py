"""Unit tests for the Week 4 MinIO load generator."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from scripts import load_generator


def client_error(status_code: int, code: str) -> ClientError:
    """Build a botocore error with a controlled S3 status and code."""
    return ClientError(
        {
            "Error": {"Code": code, "Message": "test"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        "PutObject",
    )


class ParseSizeTests(unittest.TestCase):
    def test_supported_units(self) -> None:
        self.assertEqual(load_generator.parse_size("1KB"), 1024)
        self.assertEqual(load_generator.parse_size("1.5MB"), 1572864)

    def test_rejects_oversized_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not exceed 1GB"):
            load_generator.parse_size("2GB")


class PercentileTests(unittest.TestCase):
    def test_linear_interpolation(self) -> None:
        self.assertEqual(load_generator.percentile([1, 2, 3, 4], 50), 2.5)

    def test_empty_input(self) -> None:
        self.assertEqual(load_generator.percentile([], 95), 0.0)


class SettingsTests(unittest.TestCase):
    def test_application_credentials_take_priority(self) -> None:
        environment = {
            "ENDPOINT_URL": "http://localhost:9000",
            "AWS_ACCESS_KEY_ID": "app-user",
            "AWS_SECRET_ACCESS_KEY": "app-secret",
            "MINIO_ROOT_USER": "root-user",
            "MINIO_ROOT_PASSWORD": "root-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_generator.load_settings()

        self.assertEqual(settings.credential_source, "application")
        self.assertEqual(settings.access_key, "app-user")

    def test_rejects_incomplete_credential_pair(self) -> None:
        with patch.dict(
            os.environ,
            {"AWS_ACCESS_KEY_ID": "app-user"},
            clear=True,
        ):
            with self.assertRaises(load_generator.ConfigurationError):
                load_generator.load_settings()


class RetryClassificationTests(unittest.TestCase):
    def test_retries_transient_s3_responses(self) -> None:
        self.assertTrue(
            load_generator.is_transient_error(client_error(500, "InternalError"))
        )
        self.assertTrue(
            load_generator.is_transient_error(client_error(429, "SlowDown"))
        )

    def test_does_not_retry_client_errors(self) -> None:
        self.assertFalse(
            load_generator.is_transient_error(client_error(403, "AccessDenied"))
        )
        self.assertFalse(
            load_generator.is_transient_error(client_error(404, "NoSuchBucket"))
        )

    @patch("scripts.load_generator.time.sleep")
    def test_transient_error_exhausts_three_attempts(self, sleep) -> None:
        attempts = 0

        def fail() -> None:
            nonlocal attempts
            attempts += 1
            raise client_error(500, "InternalError")

        with self.assertRaises(load_generator.OperationFailed) as context:
            load_generator.run_with_retry(fail, "test upload")

        self.assertEqual(attempts, 3)
        self.assertEqual(context.exception.attempts, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_non_transient_error_stops_after_one_attempt(self) -> None:
        attempts = 0

        def fail() -> None:
            nonlocal attempts
            attempts += 1
            raise client_error(403, "AccessDenied")

        with self.assertRaises(load_generator.OperationFailed) as context:
            load_generator.run_with_retry(fail, "test upload")

        self.assertEqual(attempts, 1)
        self.assertEqual(context.exception.attempts, 1)


class WorkloadGuardTests(unittest.TestCase):
    def test_accepts_safe_inflight_payload(self) -> None:
        total, inflight = load_generator.validate_workload(
            num_files=5000,
            threads=8,
            file_size_bytes=100 * 1024,
        )
        self.assertEqual(total, 512000000)
        self.assertEqual(inflight, 819200)

    def test_rejects_excessive_inflight_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds 512MiB"):
            load_generator.validate_workload(
                num_files=10,
                threads=10,
                file_size_bytes=1024**3,
            )


if __name__ == "__main__":
    unittest.main()
