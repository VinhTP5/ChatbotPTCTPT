# 🛠️ Scripts — Hướng dẫn nhanh

Tất cả script nằm trong `scripts/`. Cả 2 hệ điều hành:

- `*.cmd` — Windows (`cmd.exe` / PowerShell)
- `*.sh`  — Linux / macOS / Git Bash

> **Lưu ý:** chạy từ thư mục gốc project (`ChatbotPTCTPT/`). Script tự `cd` về root, nên bạn có thể chạy từ đâu cũng được — miễn đường dẫn tới script đúng.

---

## 1) Build & quản lý ChromaDB

### `build_db` — build **một** collection

| Tham số | Tuỳ chọn                                       | Mặc định  |
|---------|------------------------------------------------|-----------|
| #1      | `chunk_variant` = `fine` / `balanced` / `coarse` | `coarse`  |
| #2      | `strategy` = `standard` / `late` / `long_late`   | `standard`|
| #3      | `embed_alias` = `minilm` / `mpnet` / `e5_base` / `e5_large` / `bge_m3` | `minilm` |
| #4      | `window_tokens` (chỉ cho `late`/`long_late`)    | `512`     |
| #5      | `window_overlap` (chỉ cho `late`/`long_late`)   | `64`      |

```bat
:: Windows
scripts\build_db.cmd                              :: minilm + coarse + standard
scripts\build_db.cmd balanced long_late bge_m3    :: BGE-M3 + 800/200 + Long Late
scripts\build_db.cmd fine standard mpnet
```

```bash
# Linux/macOS
scripts/build_db.sh
scripts/build_db.sh balanced long_late bge_m3 512 64
```

### `build_all_variants` — chạy ma trận A/B sẵn

Build 6 cấu hình tiêu chuẩn để so sánh nhanh, kết thúc bằng `--mode status`.

```bat
scripts\build_all_variants.cmd
```
```bash
scripts/build_all_variants.sh
```

Cấu hình build:
1. `coarse / standard / minilm` (baseline)
2. `balanced / standard / mpnet`
3. `fine / standard / mpnet`
4. `balanced / late / mpnet`
5. `balanced / long_late / bge_m3`
6. `fine / long_late / bge_m3`

### `db_status` — xem thống kê

```bat
scripts\db_status.cmd                              :: liệt kê tất cả collection
scripts\db_status.cmd bge_m3 balanced long_late    :: chỉ collection cụ thể
```
```bash
scripts/db_status.sh
scripts/db_status.sh bge_m3 balanced long_late
```

---

## 2) Workflow git (chia nhỏ cho dễ kiểm soát)

Mỗi bước = 1 script. Đây là vòng đời chuẩn:

```
git_init   → git_status → git_add → git_diff → git_commit → git_push
                              ↑                                 │
                              └─────── git_rebase ←─────────────┘
```

### `git_init` — chỉ chạy lần đầu

```bat
scripts\git_init.cmd https://github.com/VinhTP5/ChatbotPTCTPT.git
scripts\git_init.cmd https://github.com/VinhTP5/ChatbotPTCTPT.git main
```
```bash
scripts/git_init.sh https://github.com/VinhTP5/ChatbotPTCTPT.git
```

### `git_status` — xem branch + remote + working tree

```bat
scripts\git_status.cmd
```
```bash
scripts/git_status.sh
```

### `git_add` — stage thay đổi theo nhóm

```bat
scripts\git_add.cmd               :: stage tất cả
scripts\git_add.cmd code          :: chỉ src/ app.py requirements.txt .env.example
scripts\git_add.cmd db            :: chỉ chroma_db/
scripts\git_add.cmd data          :: chỉ data/
scripts\git_add.cmd src app.py    :: stage cụ thể
```

### `git_diff` — xem diff

```bat
scripts\git_diff.cmd              :: working tree (chưa stage)
scripts\git_diff.cmd staged       :: nội dung đã stage
scripts\git_diff.cmd stat         :: chỉ thống kê dòng ± gọn
```

### `git_commit`

```bat
scripts\git_commit.cmd "Build DB: bge_m3/balanced/long_late"
scripts\git_commit.cmd                 :: mở editor để viết message dài
```

Script tự kiểm tra staging có gì không — nếu rỗng nó dừng và bảo bạn `git_add` trước.

### `git_push`

```bat
scripts\git_push.cmd              :: push branch hiện tại lên origin
scripts\git_push.cmd lease        :: --force-with-lease (an toàn hơn force)
scripts\git_push.cmd force        :: --force (xác nhận trước khi chạy)
```

### `git_rebase` — đồng bộ với main mới nhất

```bat
scripts\git_rebase.cmd                :: fetch + rebase lên origin/main
scripts\git_rebase.cmd continue       :: sau khi resolve conflict
scripts\git_rebase.cmd abort          :: huỷ
```

---

## 3) `deploy` — gộp build + commit + push (một câu lệnh)

Cho lúc bạn đã thông thạo workflow và muốn 1 lệnh chạy hết:

```bat
scripts\deploy.cmd balanced long_late bge_m3
```
```bash
scripts/deploy.sh balanced long_late bge_m3
```

Script sẽ:
1. Build collection theo cấu hình
2. `git add` các thư mục liên quan
3. Hiển thị `git diff --cached --stat`
4. Hỏi xác nhận `[y/N]` trước khi commit + push

> Khi đang debug nên dùng các script tách rời ở mục 2 thay vì `deploy` để chủ động hơn.

---

## 4) Common workflows

### A. Build collection mới + đẩy lên GitHub

```bat
scripts\build_db.cmd balanced long_late bge_m3
scripts\db_status.cmd bge_m3 balanced long_late      :: verify
scripts\git_add.cmd db                                :: chỉ stage chroma_db
scripts\git_diff.cmd stat                             :: kiểm tra trước commit
scripts\git_commit.cmd "Add bge_m3/balanced/long_late collection"
scripts\git_push.cmd
```

### B. Cập nhật code + giữ DB nguyên

```bat
scripts\git_status.cmd
scripts\git_add.cmd code
scripts\git_diff.cmd staged
scripts\git_commit.cmd "Tune retrieval defaults"
scripts\git_push.cmd
```

### C. Đồng bộ sau khi đồng đội đã push

```bat
scripts\git_rebase.cmd                :: lấy commit mới + rebase commit của mình
:: nếu có conflict, resolve trong editor rồi:
scripts\git_rebase.cmd continue
scripts\git_push.cmd lease            :: dùng --force-with-lease vì lịch sử đã đổi
```

### D. Một lệnh deploy

```bat
scripts\deploy.cmd balanced long_late bge_m3
```

---

## 5) Troubleshooting

| Triệu chứng                                | Nguyên nhân & cách xử lý                                                          |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| `Khong co thay doi nao trong staging area` | Chưa `git_add`. Chạy `scripts\git_add.cmd` trước.                                  |
| `! [rejected] main -> main (fetch first)`  | Remote có commit mới. Chạy `scripts\git_rebase.cmd` rồi push lại.                  |
| Build DB nặng (~GB) push chậm              | Cân nhắc Git LFS — xem `.gitattributes`.                                           |
| Build báo `Khong tim thay tai lieu nao`    | `data/` rỗng hoặc sai đường dẫn. Kiểm tra `data/QD` và `data/TT32_2018` tồn tại.   |
| `transformers tokenizers` xung đột phiên bản | Chạy `pip install -U transformers` để đồng bộ.                                    |
| Long Late Chunking RAM cao                 | Giảm `window_tokens` (tham số #4), hoặc đổi embedding nhẹ hơn (mpnet thay bge_m3). |
