# 🚀 Hướng dẫn Deploy

Tài liệu này hướng dẫn **cài đặt local → build vector DB → deploy lên Streamlit Cloud**.
Phiên bản hiện tại hỗ trợ **multi-collection** (embedding × chunk variant × chunking strategy).

---

## 📂 Cấu trúc thư mục

```
ChatbotPTCTPT/
├── app.py                 ← Entry Streamlit (giữ ở root)
├── requirements.txt
├── README.md
├── .env.example          ← Mẫu biến môi trường — copy thành .env
├── .gitignore  .gitattributes
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
│
├── src/                   ← MODULE PYTHON CỦA APP
│   ├── config.py          ← Cấu hình tập trung (paths, providers, embeddings, chunking)
│   ├── llm_providers.py   ← Factory đa LLM (Groq/OpenAI/Claude/Gemini/DeepSeek)
│   ├── document_loader.py ← Loader + standard chunker + metadata đầy đủ
│   ├── late_chunking.py   ← LateChunkingEmbedder (Algorithm 2)
│   ├── rag_engine.py      ← Lõi RAG (multi-collection + MMR + filter category)
│   └── build_db.py        ← CLI build/manage ChromaDB
│
├── scripts/               ← Helper scripts (build + git workflow)
│   ├── build_db.cmd|.sh
│   ├── build_all_variants.cmd|.sh
│   ├── db_status.cmd|.sh
│   ├── deploy.cmd|.sh
│   └── git_*.cmd|.sh     (init/status/add/diff/commit/push/rebase)
│
├── data/                  ← TÀI LIỆU NGUỒN (push lên GitHub)
│   ├── QD/                ← Quyết định FPT
│   └── TT32_2018/         ← Thông tư 32/2018 — Bộ GD
│
├── chroma_db/             ← VECTOR DB — mỗi cấu hình 1 collection
│   ├── indexed_files__<collection>.json
│   └── <collection-uuid>/
│
└── docs/                  ← Tài liệu dự án
    ├── DEPLOY.md          (file này)
    ├── SCRIPTS.md         (hướng dẫn từng script)
    ├── LICENSE
    └── ChatbotPTCTPT.ipynb
```

---

## 1️⃣ Chuẩn bị môi trường

```bash
pip install -r requirements.txt
cp .env.example .env       # Windows: copy .env.example .env
```

Vào `.env`, điền **ít nhất một** API key của LLM provider:

| Provider              | Biến môi trường       | Lấy key tại                                      |
|-----------------------|------------------------|--------------------------------------------------|
| Groq                  | `GROQ_API_KEY`         | https://console.groq.com                          |
| OpenAI                | `OPENAI_API_KEY`       | https://platform.openai.com                       |
| Anthropic Claude      | `ANTHROPIC_API_KEY`    | https://console.anthropic.com                     |
| Google Gemini         | `GOOGLE_API_KEY`       | https://aistudio.google.com/app/apikey            |
| DeepSeek              | `DEEPSEEK_API_KEY`     | https://platform.deepseek.com/api_keys            |

App **tự phát hiện** provider nào có key → hiện trong sidebar.

Tuỳ chọn override URL nguồn tài liệu:

```bash
CHATBOT_GH_OWNER=VinhTP5
CHATBOT_GH_REPO=ChatbotPTCTPT
CHATBOT_GH_BRANCH=main
CHATBOT_GH_DATA_PREFIX=data
# Hoặc override toàn bộ:
CHATBOT_DOC_DOMAIN=https://your.cdn/docs
CHATBOT_DOC_RAW_DOMAIN=https://your.cdn/raw
```

---

## 2️⃣ Build vector DB

### Khái niệm: **Collection naming**

Mỗi cấu hình lưu thành 1 collection riêng:

```
{embed_alias}__{chunk_variant}__{chunking_strategy}
```

Ví dụ:
- `minilm__coarse__standard` (baseline cũ)
- `mpnet__balanced__late`
- `bge_m3__fine__long_late`

App tự kiểm tra collection nào đã được build → hiện trong dropdown sidebar.
Người dùng chỉ chọn được cấu hình đã build sẵn.

### Build 1 collection (đơn giản nhất)

```bash
# Linux/macOS
scripts/build_db.sh balanced long_late bge_m3

# Windows
scripts\build_db.cmd balanced long_late bge_m3
```

Hoặc gọi trực tiếp Python (đầy đủ tham số):

```bash
python src/build_db.py --mode rebuild --force \
    --embed-model bge_m3 \
    --chunk-variant balanced \
    --chunking-strategy long_late \
    --window-tokens 512 \
    --window-overlap 64
```

### Build cả ma trận A/B

```bash
scripts/build_all_variants.sh
# hoặc
scripts\build_all_variants.cmd
```

Mặc định build 6 cấu hình tiêu chuẩn (xem `docs/SCRIPTS.md` để biết chi tiết).

### Quản lý collection

```bash
# Liệt kê tất cả collection
scripts/db_status.sh

# Trạng thái 1 collection cụ thể
scripts/db_status.sh bge_m3 balanced long_late

# Thêm 1 file mới vào collection có sẵn (incremental)
python src/build_db.py --mode add --file "QD 499.pdf" \
    --embed-model bge_m3 --chunk-variant balanced --chunking-strategy long_late

# Xoá 1 văn bản khỏi collection
python src/build_db.py --mode remove --file "QD 499.pdf" \
    --embed-model bge_m3 --chunk-variant balanced --chunking-strategy long_late
```

---

## 3️⃣ Chạy app local

```bash
streamlit run app.py
```

Mở trình duyệt tại http://localhost:8501. Trong sidebar:

1. **🔌 Provider** — auto detect từ `.env`
2. **🤖 Model** — chọn model của provider đó
3. **🧠 Embedding alias** — chỉ hiện những alias đã có collection
4. **🧩 Chunk variant + strategy** — chỉ hiện những combo đã build
5. **📚 Nguồn tài liệu** — checkbox FPT / Bộ GD (bỏ chọn để giảm vector phải duyệt)
6. **⚙️ Nâng cao** — search_type (similarity/MMR/score_threshold), fetch_k, lambda_mult, score_threshold, temperature, max_tokens, **🔍 debug retrieval toggle**
7. Bấm **🚀 Khởi động Chatbot** → đặt câu hỏi

---

## 4️⃣ Workflow git (đẩy lên GitHub)

> Toàn bộ workflow git được tách thành scripts riêng — xem `docs/SCRIPTS.md`.

### Lần đầu (1 lần duy nhất)

```bash
scripts/git_init.sh https://github.com/USER/ChatbotPTCTPT.git main
```

### Workflow thường ngày

```bash
scripts/git_status.sh                       # xem branch + working tree
scripts/git_add.sh db                       # stage chroma_db (hoặc 'code', 'data', hoặc các path cụ thể)
scripts/git_diff.sh staged                  # kiểm tra trước khi commit
scripts/git_commit.sh "Build DB: balanced/long_late/bge_m3"
scripts/git_push.sh                          # push lên origin
```

### Khi remote có commit mới (đồng đội đã push)

```bash
scripts/git_rebase.sh                       # fetch + rebase lên origin/main
# nếu có conflict — resolve trong editor → rồi:
scripts/git_rebase.sh continue
scripts/git_push.sh lease                   # force-with-lease vì lịch sử đã thay đổi
```

### One-liner (build + commit + push)

```bash
scripts/deploy.sh balanced long_late bge_m3
```

---

## 5️⃣ Deploy lên Streamlit Cloud

1. Đảm bảo đã push đủ: `data/`, `chroma_db/`, `src/`, `app.py`, `requirements.txt` lên GitHub.
2. Vào https://share.streamlit.io → **New app**.
3. Chọn repo, branch `main`, **Main file path** = `app.py`.
4. **Advanced settings → Secrets** — dán key:
   ```toml
   GROQ_API_KEY = "gsk_..."
   OPENAI_API_KEY = "sk-..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   GOOGLE_API_KEY = "AIza..."
   DEEPSEEK_API_KEY = "sk-..."
   CHATBOT_DEFAULT_PROVIDER = "groq"
   ```
5. Bấm **Deploy** → sau ~2-3 phút sẽ có URL.

> Nếu `chroma_db/` hoặc `data/` > 100 MB, bật **Git LFS** (xem `.gitattributes`).

---

## 6️⃣ Provider & Model

| Provider  | Env var               | Model mặc định            | Ghi chú                          |
|-----------|-----------------------|---------------------------|----------------------------------|
| Groq      | `GROQ_API_KEY`        | `llama-3.3-70b-versatile` | Miễn phí tier rộng, rất nhanh    |
| OpenAI    | `OPENAI_API_KEY`      | `gpt-4o-mini`             | Cân bằng giá/chất lượng          |
| Anthropic | `ANTHROPIC_API_KEY`   | `claude-3-5-sonnet-latest`| Mạnh nhất cho suy luận           |
| Google    | `GOOGLE_API_KEY`      | `gemini-1.5-flash`        | Context dài, miễn phí cao        |
| DeepSeek  | `DEEPSEEK_API_KEY`    | `deepseek-chat`           | OpenAI-compatible, rẻ, tiếng Việt tốt |

Thêm/sửa model trong `src/config.py` → `PROVIDERS`.

---

## 7️⃣ Embedding & chunking

### Embedding models (`EMBED_MODELS` trong `src/config.py`)

| Alias     | Model HF                                                       | Đặc điểm                       |
|-----------|----------------------------------------------------------------|--------------------------------|
| `minilm`  | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`  | 384-dim, nhẹ nhất, baseline    |
| `mpnet`   | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`  | 768-dim, mạnh hơn MiniLM       |
| `e5_base` | `intfloat/multilingual-e5-base`                                 | Top retrieval benchmark        |
| `e5_large`| `intfloat/multilingual-e5-large`                                | Mạnh hơn nữa, nặng hơn         |
| `bge_m3`  | `BAAI/bge-m3`                                                    | SOTA multilingual, context dài |

### Chunk variants (`CHUNK_VARIANTS`)

| Variant    | chunk_size / overlap | Use case                                       |
|------------|-----------------------|------------------------------------------------|
| `fine`     | 256 / 128             | Câu hỏi rất cụ thể, cần locate điều/khoản     |
| `balanced` | 800 / 200             | Sweet spot — recommend                         |
| `coarse`   | 1000 / 150            | Câu hỏi tổng quát, context dài (baseline cũ)   |

### Chunking strategies (`CHUNKING_STRATEGIES`)

| Strategy    | Cách hoạt động                                                                                                            |
|-------------|---------------------------------------------------------------------------------------------------------------------------|
| `standard`  | Chunk text → embed từng chunk độc lập. Đơn giản, nhanh build.                                                              |
| `late`      | Embed toàn document trước → pool theo chunk boundary. Mỗi chunk "nhìn thấy" ngữ cảnh toàn document. (Yêu cầu document ≤ max_seq_length của embedder)  |
| `long_late` | Cho document dài hơn max_seq: slide overlapping windows (kích thước `window_tokens`, overlap `window_overlap`), ghép token-embedding, rồi pool. (Algorithm 2 — Long Late Chunking)                  |

---

## 8️⃣ Metadata gán cho mỗi chunk

| Trường         | Kiểu  | Ghi chú                                        |
|----------------|-------|------------------------------------------------|
| document_name  | str   | Tên file không có ext                          |
| file_name      | str   | Tên file đầy đủ                                |
| file_path      | str   | Đường dẫn tương đối từ `data/`                 |
| file_type      | str   | `.pdf`, `.docx`, …                             |
| file_size_kb   | float | Dung lượng (KB)                                |
| source_url     | str   | GitHub blob (xem online)                       |
| raw_url        | str   | raw.githubusercontent (tải file)               |
| page_number    | int?  | Số trang (PDF), `None` với loại khác           |
| chunk_index    | int   | 1-based                                        |
| total_chunks   | int   | Tổng chunk của file                            |
| indexed_at     | str   | ISO 8601 UTC                                   |
| category       | str   | Thư mục cha (`QD`, `TT32_2018`)                |
| language       | str   | `vi`                                           |
| char_count     | int   | Số ký tự của chunk                             |

---

## 9️⃣ Định dạng tài liệu hỗ trợ

`.pdf` `.docx` `.doc` `.xlsx` `.xls` `.pptx` `.ppt`
`.txt` `.md` `.csv` `.html` `.htm`

---

## 🔧 Troubleshooting

| Triệu chứng                                | Cách xử lý                                                                                  |
|--------------------------------------------|---------------------------------------------------------------------------------------------|
| Sidebar không hiện provider                | Chưa có key nào trong `.env` hoặc Streamlit Secrets. Set ít nhất 1 key.                     |
| Không thấy embedding alias trong dropdown   | Chưa build collection cho alias đó. Chạy `scripts/build_db.cmd <variant> <strategy> <alias>`. |
| Collection báo "Chưa có trong DB"           | Cần build trước. Xem mục **2️⃣ Build vector DB**.                                            |
| `ImportError: tokenizers>=0.22,<=0.23`     | Chạy `pip install -U transformers`.                                                          |
| Push bị `! [rejected] main -> main`        | Remote có commit mới. Chạy `scripts/git_rebase.cmd` rồi `git_push.cmd`.                     |
| Long Late Chunking OOM                     | Giảm `window_tokens` xuống 384 hoặc đổi sang embedding nhẹ hơn.                              |
