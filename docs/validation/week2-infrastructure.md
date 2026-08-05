# Week 2 Infrastructure Validation

## Scope

Validation này kiểm tra phần Team Lead: MinIO distributed, Docker network, Nginx S3 endpoint, persistence và failure behavior cơ bản. Không sửa hoặc chạy code trong /scripts.

## Source inspection

- Có 4 service: minio1, minio2, minio3, minio4.
- Cả 4 node dùng command server http://minio{1...4}/data{1...2}.
- Mỗi node có /data1 và /data2 với named volume riêng.
- Có 8 data volume.
- MinIO và Nginx cùng tham gia network minio-net.
- Nginx upstream trỏ tới minio1:9000, minio2:9000, minio3:9000 và minio4:9000.
- Credential Compose bắt buộc lấy từ .env.
- .env được ignore và không nằm trong git index.
- MinIO image được pin bằng digest:
  minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e
- MinIO có readiness healthcheck; Nginx có HTTP healthcheck trên 127.0.0.1:9000.
- Prometheus hiện chỉ self-scrape, chưa scrape MinIO metrics.

## Runtime evidence

### Compose

Command:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
~~~

Result: PASS, exit code 0.

Command:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml ps
~~~

Result:

- minio1: Up, healthy
- minio2: Up, healthy
- minio3: Up, healthy
- minio4: Up, healthy
- nginx: Up, healthy
- prometheus: Up
- grafana: Up

### Network DNS

From Nginx container, getent hosts resolved all four names:

- minio1 -> 172.19.0.5
- minio2 -> 172.19.0.4
- minio3 -> 172.19.0.3
- minio4 -> 172.19.0.2

Result: PASS.

### Health endpoints

Commands:

~~~powershell
curl.exe -i http://localhost:9000/minio/health/live
curl.exe -i http://localhost:9000/minio/health/ready
~~~

Result:

- live: HTTP 200
- ready: HTTP 200

### Distributed cluster

Command used through the Nginx service name:

~~~powershell
docker run --rm --network minio-net --env-file .env --entrypoint /bin/sh minio/mc:latest -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc admin info myminio'
~~~

Observed:

- minio1, minio2, minio3, minio4
- Network: 4/4 OK
- Each node: Drives: 2/2 OK
- Pool: 1
- 8 drives online, 0 offline
- EC:4

Conclusion: validated as distributed MinIO.

### Bucket and S3 route

Bucket smoke test through Nginx created and listed test-bucket successfully.

Upload/download test:

- Source: test-t2.txt, 11 B
- Destination object: test-bucket/test-t2.txt
- Upload: PASS
- Download: PASS
- SHA256 source: ABC11A5C75B0F263C9859311DA18FC47087C89D11ADA8F0C0BC4EA9A4761C6E9
- SHA256 downloaded: ABC11A5C75B0F263C9859311DA18FC47087C89D11ADA8F0C0BC4EA9A4761C6E9
- Checksum: MATCH

### Persistence

Procedure:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml down
docker compose --env-file .env -f infra/docker-compose.yml up -d
~~~

Result:

- Cluster recreated without -v.
- test-bucket/test-t2.txt remained available.
- Download after restart succeeded.
- SHA256 remained identical.

Conclusion: persistence verified for the tested object and named volumes.

### One-node failure

Procedure:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml stop minio4
~~~

Observed while minio4 was stopped:

- minio1, minio2 and minio3 reported Network: 3/4 OK.
- minio4 reported offline.
- 6 drives online and 2 drives offline.
- EC:4 remained visible.
- mc ls succeeded.
- Upload of test-after-stop.txt succeeded through Nginx.

Recovery:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml start minio4
~~~

Result: minio4 returned to healthy and cluster returned to 4/4 network, 8 drives online.

This is a basic lab failure test, not proof of production failure-domain isolation.

## Known gaps

- Prometheus does not yet scrape MinIO metrics.
- Prometheus and Grafana do not have explicit Compose healthchecks.
- connect_test.py is not present in the integrated branch.
- mc_setup.sh still needs Member 3 review for the required three buckets.
- The Docker topology uses one host, so it does not model independent physical failure domains.
- Week 1 PNG/research/validation artifacts remain on fix/week1-finalization until its PR is merged into develop.

## Final verdict

- Distributed MinIO: PASS.
- Four node and eight volume topology: PASS.
- Internal DNS and network: PASS.
- Nginx health and S3 routing: PASS.
- Secret handling: PASS by source inspection.
- Upload/download and checksum: PASS.
- Persistence: PASS.
- One-node basic failure test: PASS for the tested read/write operation.
- Production readiness: NOT CLAIMED.
- Monitoring completeness: NOT COMPLETE.
