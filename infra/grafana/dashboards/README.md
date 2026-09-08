# Grafana dashboards

`minio-cluster-overview.json` is provisioned automatically when Grafana starts.
It contains the five Week 4 panels required by the lab:

- throughput;
- S3 request rate;
- storage usage;
- object count;
- MinIO scrape target health.

The datasource and dashboard provider live under `../provisioning/`. Do not edit
the provisioned dashboard in the Grafana UI because the version-controlled JSON
is the source of truth.
