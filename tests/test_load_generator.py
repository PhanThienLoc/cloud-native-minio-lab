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
            "DISTRIBUTED_ENDPOINT_URL": "http://distributed.example:9000",
            "AWS_ACCESS_KEY_ID": "app-user",
            "AWS_SECRET_ACCESS_KEY": "app-secret",
            "MINIO_ROOT_USER": "root-user",
            "MINIO_ROOT_PASSWORD": "root-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_generator.load_settings("distributed")

        self.assertEqual(settings.credential_source, "application")
        self.assertEqual(settings.access_key, "app-user")
        self.assertEqual(
            settings.endpoint_url,
            "http://distributed.example:9000",
        )

    def test_rejects_incomplete_credential_pair(self) -> None:
        with patch.dict(
            os.environ,
            {"AWS_ACCESS_KEY_ID": "app-user"},
            clear=True,
        ):
            with self.assertRaises(load_generator.ConfigurationError):
                load_generator.load_settings("distributed")

    def test_standalone_mode_uses_standalone_endpoint(self) -> None:
        environment = {
            "ENDPOINT_URL": "http://must-not-be-used:9999",
            "STANDALONE_ENDPOINT_URL": "http://standalone.example:9001",
            "MINIO_ROOT_USER": "root-user",
            "MINIO_ROOT_PASSWORD": "root-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_generator.load_settings("standalone")

        self.assertEqual(
            settings.endpoint_url,
            "http://standalone.example:9001",
        )

    def test_distributed_mode_uses_distributed_endpoint(self) -> None:
        environment = {
            "ENDPOINT_URL": "http://must-not-be-used:9999",
            "DISTRIBUTED_ENDPOINT_URL": "http://distributed.example:9000",
            "MINIO_ROOT_USER": "root-user",
            "MINIO_ROOT_PASSWORD": "root-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_generator.load_settings("distributed")

        self.assertEqual(
            settings.endpoint_url,
            "http://distributed.example:9000",
        )

    def test_missing_credentials_fail_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                load_generator.ConfigurationError,
                "Set application credentials or both MinIO root variables",
            ):
                load_generator.load_settings("distributed")

    def test_complete_root_credentials_are_accepted(self) -> None:
        environment = {
            "MINIO_ROOT_USER": "root-user",
            "MINIO_ROOT_PASSWORD": "root-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_generator.load_settings("standalone")

        self.assertEqual(settings.credential_source, "root-lab")
        self.assertEqual(settings.access_key, "root-user")
        self.assertEqual(settings.endpoint_url, "http://localhost:9001")

    def test_rejects_example_placeholder_credentials(self) -> None:
        environment = {
            "MINIO_ROOT_USER": "change-me",
            "MINIO_ROOT_PASSWORD": "change-me-minio-password",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(
                load_generator.ConfigurationError,
                "placeholder credentials",
            ):
                load_generator.load_settings("distributed")

    def test_rejects_incomplete_root_credential_pair(self) -> None:
        with patch.dict(
            os.environ,
            {"MINIO_ROOT_USER": "root-user"},
            clear=True,
        ):
            with self.assertRaises(load_generator.ConfigurationError):
                load_generator.load_settings("standalone")

    def test_rejects_unknown_mode(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MINIO_ROOT_USER": "root-user",
                "MINIO_ROOT_PASSWORD": "root-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                load_generator.ConfigurationError,
                "Unsupported benchmark mode",
            ):
                load_generator.load_settings("invalid")


class ReportContextTests(unittest.TestCase):
    @patch("scripts.load_generator.host_context")
    @patch("scripts.load_generator.working_tree_is_dirty")
    @patch("scripts.load_generator.git_output")
    def test_report_contains_reproducibility_context(
        self,
        git_output,
        working_tree_is_dirty,
        host_context,
    ) -> None:
        git_output.side_effect = ["feature/benchmark-cli", "abc123"]
        working_tree_is_dirty.return_value = False
        host_context.return_value = {
            "cpu_count": 8,
            "memory_gib": 16.0,
        }
        settings = load_generator.S3Settings(
            endpoint_url="http://localhost:9001",
            access_key="user",
            secret_key="secret",
            credential_source="root-lab",
        )

        report = load_generator.build_report(
            settings=settings,
            bucket_name="benchmark-bucket",
            topology="standalone",
            object_prefix="load-test/run_id=test",
            num_files=1,
            threads=1,
            file_size_bytes=1024,
            results=[
                {
                    "object_index": 1,
                    "success": True,
                    "latency_ms": 1.0,
                    "bytes": 1024,
                    "attempts": 1,
                    "error": "",
                }
            ],
            total_duration=1.0,
        )

        context = report["context"]
        self.assertEqual(context["git"]["branch"], "feature/benchmark-cli")
        self.assertEqual(context["git"]["commit"], "abc123")
        self.assertFalse(context["git"]["working_tree_dirty"])
        self.assertEqual(context["host"]["memory_gib"], 16.0)
        self.assertEqual(context["runtime"]["image"], load_generator.MINIO_IMAGE)
        self.assertEqual(context["runtime"]["total_cpu_limit"], 4.0)
        self.assertEqual(context["runtime"]["total_memory_gib"], 4.0)


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
