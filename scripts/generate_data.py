import os
import random
import csv
from faker import Faker
from tqdm import tqdm

fake = Faker()

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(DATA_DIR, exist_ok = True)

#file van ban
def generate_logs(filename, target_size_mb = 30):
    """ tạo file log dạng văn bản thô """
    print(f"đang tạo file log ({target_size_mb} MB).....")
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0

    with open(filename, "w", encoding="utf-8") as f:
        with tqdm(total=target_bytes, unit = "B" ,unit_scale = True, desc = "Logs") as pbar:
            while current_bytes < target_bytes:
                log_entry = f"{fake.date_time_this_year()} [{fake.http_method()}] - {fake.ipv4_private()} - Status: {random.choice([200, 404, 500])}\n"
                f.write(log_entry)
                bytes_written = len(log_entry.encode("utf-8"))
                current_bytes += bytes_written
                pbar.update(bytes_written)

def generate_csv(filename, target_size_mb = 30):
    """tạo file csv cấu trúc """
    print(f"đang tạo file csv ({target_size_mb} MB)......")
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0

    with open(filename, "w", newline="", encoding = "utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Email", "Job", "Address", "Created_At"])

        with tqdm(total=target_bytes, unit="B", unit_scale=True, desc = "CSV") as pbar:
            while current_bytes < target_bytes:
                row = [
                    fake.uuid4(), 
                    fake.name(), 
                    fake.email(), 
                    fake.job(), 
                    fake.address().replace("\n", " "), 
                    fake.iso8601()
                ]
                writer.writerow(row)
                bytes_written = len(",".join(row).encode("utf-8")) + 2
                current_bytes += bytes_written
                pbar.update(bytes_written)  

def generate_dummy_binary(folder_path, count=100, size_kb=200):
    """Tạo bộ file nhị phân dummy (mô phỏng ảnh)"""
    print(f" Đang tạo {count} file nhị phân dummy (~{size_kb} KB/file)...")
    os.makedirs(folder_path, exist_ok=True)
    
    for i in tqdm(range(count), desc="Binary Images"):
        file_path = os.path.join(folder_path, f"image_dummy_{i+1}.bin")
        with open(file_path, "wb") as f:
            f.write(os.urandom(size_kb * 1024))

if __name__ == "__main__":
    print(" Bắt đầu sinh dataset mẫu cho MinIO Lab...\n")
    
    # 1. Tạo 30MB file Log
    generate_logs(os.path.join(DATA_DIR, "system_logs.log"), target_size_mb=30)
    
    # 2. Tạo 30MB file CSV
    generate_csv(os.path.join(DATA_DIR, "user_data.csv"), target_size_mb=30)
    
    # 3. Tạo 100 file nhị phân dummy tổng khoảng 20MB
    generate_dummy_binary(os.path.join(DATA_DIR, "dummy_images"), count=100, size_kb=200)
    
    print(f"\n Đã tạo xong bộ dataset mẫu (~80MB) tại: {DATA_DIR}")