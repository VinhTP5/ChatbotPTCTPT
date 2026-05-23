# ChatbotPTCTPT

Chatbot RAG (Retrieval-Augmented Generation) tư vấn về Phát triển Chương trình Giáo dục Phổ thông.

## ✨ Tính năng

- **Đa nhà cung cấp LLM** — Groq, OpenAI, Anthropic Claude, Google Gemini (dev cấu hình env).
- **User KHÔNG cần API key** — toàn bộ key do dev tích hợp.
- **Nhiều định dạng** — PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, TXT, MD, CSV, HTML.
- **Metadata đầy đủ** mỗi chunk — file, path, page, chunk_index, indexed_at, category, language, …
- **URL nguồn trỏ thẳng tới GitHub** — xem online (`source_url`) hoặc tải về (`raw_url`).
- **CLI build_db** — rebuild / add / remove / status.
- **Multi-collection indexing** — embed/chunk/strategy tách collection riêng.
- **Advanced retrieval** — similarity, MMR, similarity with score threshold.
- **UI chatbot-first** — sidebar thu gọn mặc định, chat input ở cuối màn hình, tự khởi động khi đủ cấu hình.
- **Runtime caching cho deploy** — tái dùng embedding model, Chroma collection và collection listing để giảm warm-up lặp lại.

## 📂 Cấu trúc

```
app.py             Entry point Streamlit (root)
src/               Module Python của app
data/              Tài liệu nguồn (push lên GitHub)
chroma_db/         Vector DB chunks (push lên GitHub)
docs/              Tài liệu dự án
```

## 🚀 Bắt đầu nhanh

```bash
pip install -r requirements.txt
cp .env.example .env                    # điền API key của ≥1 provider
python src/build_db.py --mode rebuild --force \
	--embed-model minilm --chunk-variant coarse --chunking-strategy standard
streamlit run app.py
```

Xem tai lieu tong hop du an trong [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md).
Xem chi tiet deploy trong [docs/DEPLOY.md](docs/DEPLOY.md) va scripts trong [docs/SCRIPTS.md](docs/SCRIPTS.md).

Tham khao quy chuan tu vung UI de thong nhat cach dung tu khi mo rong giao dien tai [../SinhdeDoAI/UI-GLOSSARY.md](../SinhdeDoAI/UI-GLOSSARY.md).

## 📝 License

Xem [`docs/LICENSE`](docs/LICENSE).
