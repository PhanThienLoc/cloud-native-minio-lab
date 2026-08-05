# Member 3 – Week 2 Validation

## 1. Kiểm tra MinIO Client

```bash
mc --version
```

Kết quả:

(Chưa kiểm thử)

---

## 2. Cấu hình alias

```bash
mc alias list
```

Kết quả:

(Chưa kiểm thử)

---

## 3. Danh sách bucket

```bash
mc ls myminio
```

Kết quả:

(Chưa kiểm thử)

---

## 4. Kiểm tra versioning

```bash
mc version info myminio/raw-data
```

Kết quả:

(Chưa kiểm thử)

---

## 5. Kiểm tra chạy lại script

```bash
bash scripts/mc_setup.sh
bash scripts/mc_setup.sh
```

Kết luận:

Chưa kiểm thử – sẽ cập nhật sau khi Docker hoàn thành.