# Chaos Engineering Scenarios

## Scenario 1: Stop one MinIO node
1. Identify the active node.
2. Stop the container.
3. Observe service continuity and recovery.

## Scenario 2: Restart the load balancer
1. Capture baseline latency.
2. Restart Nginx.
3. Record impact on availability.

## Scenario 3: Validate RTO/RPO
1. Trigger a controlled failure.
2. Measure recovery time.
3. Compare recovered data with the last successful upload.
