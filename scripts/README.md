Kích hoạt môi trường ảo venv
.\venv\Scripts\Activate.ps1

1. Cài đặt phụ thuộc

PowerShell
python -m pip install --upgrade pip
python -m pip install python-dotenv boto3 numpy matplotlib

check xem các gói oke chưa 

python -c "import dotenv, boto3, numpy, matplotlib; print('Môi trường đã sẵn sàng!')"

2. Kịch bản A: Test với 1 Node (Standalone)

Bước 1: Dọn dẹp các container cũ

PowerShell
docker rm -f minio-standalone
docker compose -f infra/docker-compose.yml down

Bước 2: Chỉ bật Prometheus và Grafana

PowerShell
docker compose -f infra/docker-compose.yml up -d --no-deps prometheus grafana

Bước 3: Khởi chạy MinIO Standalone (dùng đúng tài khoản minioadmin)

PowerShell
docker run -d --name minio-standalone --network minio-net -p 9001:9000 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio/minio server /data

Bước 4: Khởi tạo bucket benchmark

PowerShell
docker exec minio-standalone mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec minio-standalone mc mb local/benchmark-bucket --ignore-existing

Bước 5: Chạy benchmark Kịch bản A

PowerShell
cd scripts
python load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode standalone --output standalone_run1

3. Kịch bản B: Test với 4 Node (Distributed)
Bước 1: Xóa node Standalone

PowerShell
docker rm -f minio-standalone

Bước 2: Bật toàn bộ cụm 4 node + Nginx + Prometheus + Grafana

PowerShell
docker compose -f ../infra/docker-compose.yml up -d

Bước 3 :Tạo bucket benchmark-bucket bằng câu lệnh MinIO Client hoặc AWS CLI:
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/benchmark-bucket --ignore-existing

Bước 4: Chạy benchmark Kịch bản B

PowerShell
python load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode distributed --output distributed_run1