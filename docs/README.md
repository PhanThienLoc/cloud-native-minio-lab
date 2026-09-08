# Documentation Index

Tài liệu được giữ tại `docs/` theo chức năng. Các file không được di chuyển chỉ
để đổi tên thư mục, nhằm bảo toàn link, evidence và lịch sử Git.

## Bắt đầu

- [Demo Flow](demo-flow.md): kịch bản demo hệ thống ngắn.
- [Project Runbook](project-runbook.md): hướng dẫn cài đặt, vận hành và kiểm tra
  theo toàn bộ tiến độ dự án.
- [Benchmark Guide](../benchmark-results/README.md): standalone/distributed,
  3 lần chạy và yêu cầu provenance.

## Kiến trúc và nghiên cứu

- [MinIO architecture](architecture/week1-minio-architecture.md)
- [Architecture source (PUML)](architecture/week1-minio-architecture.puml)
- [Erasure Coding and Sharding research](research/minio-erasure-coding-and-sharding.md)

## Validation

- [Week 1 data generation](validation/week1-data-generator.md)
- [Week 2 infrastructure](validation/week2-infrastructure.md)
- [Week 2 connection test](validation/week2-member2-connection-test.md)
- [Week 3 ingestion](validation/week3-member2-data-ingestion.md)
- [Week 3 infrastructure](validation/week3-teamlead-infrastructure.md)
- [Week 4 observability](validation/week4-observability.md)
- [Week 4 load generator](validation/week4-member2-load-test.md)
- [Week 5 readiness](validation/week5-teamlead-readiness.md)
- [Week 6 resilience and chaos](validation/week6-basic-chaos-and-resilience.md)
- [Checksum and bucket setup](validation/member3-checksum-and-mc.md)

## Governance, reports and handoff

- [Week 5 code-freeze policy](governance/week5-code-freeze.md)
- [Final report chapters](reports/chapter-1-6.md)
- [Benchmark aggregate](reports/benchmark_aggregate.csv)
- [Slide handoff](meeting_logs/week5-slide-handoff.md)

## Maintenance rule

Khi thêm tài liệu mới, đặt file vào nhóm hiện có và thêm link ngắn tại index này
nếu tài liệu hữu ích cho người chạy hoặc đánh giá dự án. Không đưa credential,
đường dẫn máy cá nhân hoặc dataset tạm vào tài liệu được commit.
