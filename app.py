"""
app.py
------
Streamlit app — Chatbot RAG đa nhà cung cấp LLM.

API key do dev tích hợp qua biến môi trường / Streamlit Secrets:
    GROQ_API_KEY        → Groq
    OPENAI_API_KEY      → OpenAI
    ANTHROPIC_API_KEY   → Anthropic Claude
    GOOGLE_API_KEY      → Google Gemini

Người dùng cuối KHÔNG cần nhập API key. App tự phát hiện provider có sẵn.
"""

from __future__ import annotations

import sys
import csv
from io import StringIO
from pathlib import Path


# ---------------------------------------------------------------------------
# Reassemble chroma.sqlite3 từ các part nếu chưa có (Streamlit Cloud deploy)
# ---------------------------------------------------------------------------
def _reassemble_sqlite() -> None:
    """Ghép chroma.sqlite3 từ các phần .part.NNN nếu file chưa tồn tại."""
    import hashlib

    db_dir  = Path(__file__).resolve().parent / "chroma_db"
    sqlite  = db_dir / "chroma.sqlite3"

    if sqlite.exists():
        return  # đã có, không cần làm gì

    parts = sorted(db_dir.glob("chroma.sqlite3.part.*"))
    if not parts:
        return  # không có part, build local thì bình thường

    print(f"[startup] Ghép {len(parts)} phần → chroma.sqlite3 ...", flush=True)
    with open(sqlite, "wb") as out:
        for part in parts:
            out.write(part.read_bytes())

    # Verify MD5 nếu có
    md5_file = db_dir / "chroma.sqlite3.md5"
    if md5_file.exists():
        expected = md5_file.read_text().strip()
        h = hashlib.md5()
        with open(sqlite, "rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            sqlite.unlink()
            raise RuntimeError("[startup] chroma.sqlite3 bị lỗi checksum — kiểm tra lại các part.")
        print(f"[startup] ✓ Checksum OK.", flush=True)
    else:
        print(f"[startup] ✓ Ghép xong.", flush=True)


_reassemble_sqlite()
# ---------------------------------------------------------------------------


# Cho phép import các module trong src/ khi chạy `streamlit run app.py` từ root
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from config import (  # noqa: E402
    CHROMA_DIR,
    CHUNKING_STRATEGIES,
    CHUNK_VARIANTS,
    DEFAULT_CHUNKING_STRATEGY,
    DEFAULT_CHUNK_VARIANT,
    DEFAULT_EMBED_ALIAS,
    DEFAULT_FETCH_K,
    DEFAULT_LAMBDA_MULT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_NEIGHBOR_K,
    DEFAULT_RERANK_TOP_N,
    DEFAULT_SCORE_THRESHOLD,
    DEFAULT_SEARCH_TYPE,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_USE_RERANK,
    EMBED_MODELS,
    MAX_TOP_K,
    MIN_TOP_K,
    PROVIDERS,
    SEARCH_TYPES,
    SOURCE_CATEGORIES,
    build_collection_name,
)
from llm_providers import (  # noqa: E402
    NoProviderConfiguredError,
    ProviderUnavailableError,
    available_providers,
    describe_status,
)
from rag_engine import load_rag_engine, list_available_collections  # noqa: E402

# ── Cấu hình trang ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot PTCT PT",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; }

    .stat-card {
        background: #f0f4f8;
        border-left: 4px solid #2d6a9f;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.8rem;
    }
    .stat-card .label { font-size: 0.75rem; color: #666; text-transform: uppercase; }
    .stat-card .value { font-size: 1.05rem; font-weight: 600; color: #1e3a5f; }
    .stat-card .meta  { font-size: 0.78rem; color: #555; margin-top: 0.2rem; }

    .source-item {
        background: #eef6ff;
        border: 1px solid #bee3f8;
        border-radius: 6px;
        padding: 0.45rem 0.7rem;
        margin: 0.25rem 0;
        font-size: 0.88rem;
    }
    .source-item .small { color: #555; font-size: 0.78rem; }

    .stChatMessage { border-radius: 10px !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Hằng số UI ────────────────────────────────────────────────────────────────
FILE_ICONS = {
    "pdf" : "📄",
    "docx": "📝", "doc": "📝",
    "xlsx": "📊", "xls": "📊",
    "pptx": "📑", "ppt": "📑",
    "txt" : "📋",
    "md"  : "📋",
    "csv" : "🧮",
    "html": "🌐", "htm": "🌐",
}


def file_icon(file_type: str) -> str:
    return FILE_ICONS.get((file_type or "").lstrip("."), "📁")


# ── Session state init ────────────────────────────────────────────────────────
_DEFAULTS = {
    "messages"           : [],
    "engine"             : None,
    "doc_count"          : 0,
    "model_loaded"       : False,
    "selected_provider"  : None,
    "selected_model"     : None,
    "selected_categories": list(SOURCE_CATEGORIES.keys()),  # mặc định: chọn tất cả
    "last_sources"       : [],
    "last_docs_with_scores": [],
    "total_questions"    : 0,
    "pending_question"   : None,
    "selected_embed_alias": DEFAULT_EMBED_ALIAS,
    "selected_chunk_variant": DEFAULT_CHUNK_VARIANT,
    "selected_chunking_strategy": DEFAULT_CHUNKING_STRATEGY,
    "debug_retrieval": False,
    "use_rerank"     : DEFAULT_USE_RERANK,
    "neighbor_k"     : DEFAULT_NEIGHBOR_K,
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _answer(question: str, debug_retrieval: bool = False) -> tuple[str, list[dict], list[dict]]:
    """Gọi engine.ask/ask_with_scores — trả về (answer, sources, docs_with_scores)."""
    try:
        if debug_retrieval:
            result = st.session_state.engine.ask_with_scores(question)
        else:
            result = st.session_state.engine.ask(question)
        return result.answer, result.sources, result.docs_with_scores
    except Exception as e:
        return f"❌ Lỗi khi xử lý câu hỏi: {e}", [], []


def _render_source_badge(src: dict) -> str:
    icon = file_icon(src.get("type", ""))
    page = src.get("page")
    cat  = src.get("category")
    size = src.get("file_size_kb")
    bits = []
    if cat:  bits.append(str(cat))
    if page: bits.append(f"trang {page}")
    if size: bits.append(f"{size} KB")
    meta = " · ".join(bits)

    view_href = src.get("url") or "#"          # GitHub blob (xem online)
    raw_href  = src.get("raw_url") or view_href  # raw (tải file)
    name      = src.get("name") or "Không rõ"

    # 2 link: Xem online (GitHub) + Tải file (raw)
    return (
        f'<div class="source-item">{icon} '
        f'<a href="{view_href}" target="_blank" title="Xem trên GitHub">{name}</a>'
        f' &nbsp;·&nbsp; <a href="{raw_href}" target="_blank" title="Tải file gốc">⬇️</a>'
        + (f'<div class="small">{meta}</div>' if meta else "")
        + "</div>"
    )


def _parse_collection_name(name: str) -> tuple[str, str, str] | None:
    parts = name.split("__")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def _built_matrix() -> dict[str, set[str]]:
    combos = list_available_collections(CHROMA_DIR)
    parsed = [p for p in (_parse_collection_name(c) for c in combos) if p is not None]
    return {
        "embed": {p[0] for p in parsed},
        "variant": {p[1] for p in parsed},
        "strategy": {p[2] for p in parsed},
        "full": {"__".join(p) for p in parsed},
    }


def _docs_with_scores_to_csv(rows: list[dict]) -> str:
    buf = StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "score",
            "document_name",
            "page_number",
            "chunk_index",
            "char_count",
            "source_url",
            "content_preview",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {
                "score": r.get("score"),
                "document_name": r.get("document_name"),
                "page_number": r.get("page_number"),
                "chunk_index": r.get("chunk_index"),
                "char_count": r.get("char_count"),
                "source_url": r.get("source_url"),
                "content_preview": r.get("content_preview"),
            }
        )
    return buf.getvalue()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Cài đặt")

    st.markdown("### 🔌 Nhà cung cấp LLM")
    avail = available_providers()
    if not avail:
        st.error(
            "Chưa có API key. Dev cần thiết lập 1 trong các biến môi trường: "
            + ", ".join(info["env_keys"][0] for info in PROVIDERS.values())
        )
    else:
        st.success(f"✅ Có {len(avail)} nhà cung cấp sẵn sàng")

    if avail:
        selected_provider = st.selectbox(
            "Provider:",
            options=avail,
            format_func=lambda p: PROVIDERS[p]["label"],
            index=0,
        )
    else:
        selected_provider = None

    if selected_provider:
        models = PROVIDERS[selected_provider]["models"]
        st.markdown("### 🤖 Model")
        selected_model = st.selectbox(
            "Model:",
            options=list(models.keys()),
            format_func=lambda x: f"{x} — {models[x]}",
            index=0,
        )
    else:
        selected_model = None

    built = _built_matrix()

    st.markdown("### 🧠 Embedding")
    embed_options = sorted(built["embed"]) if built["embed"] else list(EMBED_MODELS.keys())
    if not built["embed"]:
        st.caption("Chưa phát hiện collection nào, đang hiển thị toàn bộ embedding alias.")

    selected_embed_alias = st.selectbox(
        "Embedding alias:",
        options=embed_options,
        index=embed_options.index(st.session_state.selected_embed_alias)
        if st.session_state.selected_embed_alias in embed_options
        else 0,
        format_func=lambda x: f"{x} — {EMBED_MODELS[x]['label']}",
    )
    st.session_state.selected_embed_alias = selected_embed_alias

    st.markdown("### 🧩 Chunking")
    variant_options = sorted(built["variant"]) if built["variant"] else list(CHUNK_VARIANTS.keys())
    selected_chunk_variant = st.selectbox(
        "Chunk variant:",
        options=variant_options,
        index=variant_options.index(st.session_state.selected_chunk_variant)
        if st.session_state.selected_chunk_variant in variant_options
        else 0,
        format_func=lambda x: CHUNK_VARIANTS[x]["label"],
    )
    strategy_options = sorted(built["strategy"]) if built["strategy"] else list(CHUNKING_STRATEGIES.keys())
    selected_chunking_strategy = st.selectbox(
        "Chunking strategy:",
        options=strategy_options,
        index=strategy_options.index(st.session_state.selected_chunking_strategy)
        if st.session_state.selected_chunking_strategy in strategy_options
        else 0,
        format_func=lambda x: CHUNKING_STRATEGIES[x],
    )
    st.session_state.selected_chunk_variant = selected_chunk_variant
    st.session_state.selected_chunking_strategy = selected_chunking_strategy

    top_k = st.slider(
        "Số đoạn tài liệu tham khảo (Top-K):",
        min_value=MIN_TOP_K, max_value=MAX_TOP_K, value=DEFAULT_TOP_K,
        help="Nhiều hơn = context rộng hơn nhưng chậm và tốn token hơn.",
    )

    # ── Nguồn tài liệu (filter category để giảm vector phải duyệt) ───────────
    st.markdown("### 📚 Nguồn tài liệu")
    st.caption("Bỏ chọn nguồn không cần để giảm request và tăng tốc.")
    selected_categories: list[str] = []
    for cat_id, info in SOURCE_CATEGORIES.items():
        if st.checkbox(
            f"{info['icon']} {info['label']}",
            value=cat_id in st.session_state.selected_categories,
            key=f"cat_{cat_id}",
            help=info["description"],
        ):
            selected_categories.append(cat_id)
    st.session_state.selected_categories = selected_categories

    if not selected_categories:
        st.warning("⚠️ Phải chọn ít nhất 1 nguồn tài liệu.")

    with st.expander("⚙️ Nâng cao"):
        search_type = st.selectbox(
            "Search type",
            options=SEARCH_TYPES,
            index=SEARCH_TYPES.index(DEFAULT_SEARCH_TYPE) if DEFAULT_SEARCH_TYPE in SEARCH_TYPES else 0,
        )
        fetch_k = st.slider(
            "Fetch-K",
            min_value=top_k,
            max_value=50,
            value=max(DEFAULT_FETCH_K, top_k),
            step=1,
            help="Số candidates trước khi chọn Top-K (hữu ích với MMR).",
        )
        lambda_mult = st.slider(
            "Lambda (MMR)",
            min_value=0.0,
            max_value=1.0,
            value=float(DEFAULT_LAMBDA_MULT),
            step=0.05,
            disabled=(search_type != "mmr"),
        )
        score_threshold = st.slider(
            "Score threshold",
            min_value=0.0,
            max_value=1.0,
            value=float(DEFAULT_SCORE_THRESHOLD or 0.3),
            step=0.05,
            disabled=(search_type != "similarity_score_threshold"),
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0, max_value=1.0, value=DEFAULT_TEMPERATURE, step=0.05,
        )
        max_tokens = st.slider(
            "Max tokens (đầu ra)",
            min_value=256, max_value=8192, value=DEFAULT_MAX_TOKENS, step=128,
        )
        debug_retrieval = st.checkbox(
            "🔍 Chế độ debug retrieval",
            value=st.session_state.debug_retrieval,
            help="Hiển thị chunk, score, metadata và export CSV sau mỗi câu trả lời.",
        )
        st.session_state.debug_retrieval = debug_retrieval

        st.markdown("**🔬 Reranker & Neighbor**")
        use_rerank = st.toggle(
            "Dùng Reranker (BGE-M3)",
            value=st.session_state.use_rerank,
            help="Xếp lại chunks theo cross-encoder score. Chính xác hơn nhưng chậm hơn ~2-3 giây.",
        )
        st.session_state.use_rerank = use_rerank

        neighbor_k = st.slider(
            "Neighbor context (±chunk)",
            min_value=0,
            max_value=3,
            value=st.session_state.neighbor_k,
            step=1,
            help="Mở rộng context bằng cách lấy thêm chunk liền kề trong cùng tài liệu. 0 = tắt.",
        )
        st.session_state.neighbor_k = neighbor_k

        if use_rerank:
            st.caption("⚠️ Reranker cần ~2-3 giây thêm mỗi câu hỏi và yêu cầu download model lần đầu.")

    target_collection = build_collection_name(
        selected_embed_alias,
        selected_chunk_variant,
        selected_chunking_strategy,
    )
    if target_collection not in built["full"]:
        st.warning("⚠️ Collection chưa có trong DB cho cấu hình đang chọn. Hãy build DB trước.")

    st.divider()

    # Nếu đã khởi động và đổi retrieval/source params → cập nhật runtime
    if (
        st.session_state.model_loaded
        and st.session_state.engine is not None
        and selected_categories
    ):
        try:
            cats_arg_runtime = (
                selected_categories
                if len(selected_categories) < len(SOURCE_CATEGORIES)
                else None
            )
            st.session_state.engine.set_retrieval_params(
                top_k=top_k,
                search_type=search_type,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                score_threshold=score_threshold if search_type == "similarity_score_threshold" else None,
                categories=cats_arg_runtime,
                use_rerank=use_rerank,
                neighbor_k=neighbor_k,
            )
        except Exception as e:
            st.error(f"Không cập nhật được retrieval: {e}")

    if st.button(
        "🚀 Khởi động Chatbot",
        type="primary",
        use_container_width=True,
        disabled=(selected_provider is None or not selected_categories or target_collection not in built["full"]),
    ):
        with st.spinner("Đang tải mô hình và kết nối database..."):
            try:
                # Nếu user chọn tất cả nguồn → không cần filter (nhanh hơn)
                cats_arg = (
                    selected_categories
                    if len(selected_categories) < len(SOURCE_CATEGORIES)
                    else None
                )
                engine, _retriever, doc_count = load_rag_engine(
                    provider    = selected_provider,
                    model_name  = selected_model,
                    top_k       = top_k,
                    search_type = search_type,
                    fetch_k     = fetch_k,
                    lambda_mult = lambda_mult,
                    score_threshold = score_threshold if search_type == "similarity_score_threshold" else None,
                    temperature = temperature,
                    max_tokens  = max_tokens,
                    embed_alias = selected_embed_alias,
                    chunk_variant = selected_chunk_variant,
                    chunking_strategy = selected_chunking_strategy,
                    categories  = cats_arg,
                    use_rerank  = use_rerank,
                    neighbor_k  = neighbor_k,
                )
                st.session_state.engine            = engine
                st.session_state.doc_count         = doc_count
                st.session_state.model_loaded      = True
                st.session_state.selected_provider = selected_provider
                st.session_state.selected_model    = selected_model
                st.session_state.messages          = []
                st.success(f"✅ Sẵn sàng! ({doc_count:,} vectors)")
            except FileNotFoundError as e:
                st.error(f"❌ {e}")
            except (NoProviderConfiguredError, ProviderUnavailableError) as e:
                st.error(f"❌ Cấu hình LLM: {e}")
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")

    st.divider()

    st.markdown("### 📊 Thống kê")
    db_exists = Path(CHROMA_DIR).exists() and any(Path(CHROMA_DIR).iterdir())
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Vectors",
            f"{st.session_state.doc_count:,}" if st.session_state.model_loaded else "—",
        )
    with col2:
        st.metric("Câu hỏi", st.session_state.total_questions)

    if st.session_state.model_loaded:
        prov = PROVIDERS[st.session_state.selected_provider]["label"]
        st.success(f"🟢 {prov} · {st.session_state.selected_model}")
        if st.session_state.engine is not None:
            st.caption(f"🗂️ {st.session_state.engine.collection_name}")
        active_cats = st.session_state.selected_categories
        if active_cats and len(active_cats) < len(SOURCE_CATEGORIES):
            badges = " · ".join(SOURCE_CATEGORIES[c]["short"] for c in active_cats)
            st.caption(f"📚 Lọc nguồn: {badges}")
        else:
            st.caption("📚 Lọc nguồn: tất cả")
    else:
        st.warning("🔴 Chưa khởi động")

    if db_exists:
        st.caption("✅ Database: sẵn sàng")
    else:
        st.caption("❌ Database: chưa có — chạy `python build_db.py` trước")

    st.divider()

    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages        = []
        st.session_state.last_sources    = []
        st.session_state.total_questions = 0
        st.rerun()

    with st.expander("📖 Hướng dẫn"):
        st.markdown(
            "**Bước 1:** Chọn provider & model ở phía trên\n\n"
            "**Bước 2:** Điều chỉnh Top-K\n\n"
            "**Bước 3:** Bấm **Khởi động Chatbot**\n\n"
            "**Bước 4:** Đặt câu hỏi trong ô chat\n\n"
            "---\n\n"
            "**Cho dev:** đặt API key vào biến môi trường — `GROQ_API_KEY`, "
            "`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`."
        )

    with st.expander("🩺 Trạng thái hệ thống"):
        st.code(describe_status(), language="text")


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
    <h1>🎓 Chatbot Tư Vấn Giáo Dục Phổ Thông</h1>
    <p>Hỏi đáp thông minh dựa trên văn bản quy định của Bộ GD&ĐT Việt Nam</p>
</div>
""",
    unsafe_allow_html=True,
)

if not st.session_state.model_loaded:
    st.markdown("### 👋 Chào mừng!")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Bước 1**\n\n🔌 Chọn LLM provider ở sidebar")
    with col2:
        st.info("**Bước 2**\n\n🤖 Chọn model phù hợp")
    with col3:
        st.info("**Bước 3**\n\n🚀 Bấm **Khởi động Chatbot**")

    st.markdown("---")
    st.markdown("### 💡 Ví dụ câu hỏi:")
    for ex in [
        "Học sinh cần đáp ứng điều kiện gì để được lên lớp?",
        "Cấu trúc chương trình GDPT 2018 gồm những gì?",
        "Quy định về đánh giá học sinh tiểu học như thế nào?",
        "Các môn học bắt buộc ở cấp THPT là gì?",
        "Điều kiện tốt nghiệp THPT theo quy định hiện hành?",
    ]:
        st.markdown(f"- *{ex}*")
    st.stop()


# ── Khu vực chat ──────────────────────────────────────────────────────────────
chat_col, source_col = st.columns([3, 1])

with chat_col:
    st.markdown("### 💬 Hội thoại")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"📚 {len(msg['sources'])} tài liệu tham khảo"):
                    for src in msg["sources"]:
                        st.markdown(_render_source_badge(src), unsafe_allow_html=True)

    question = st.chat_input("Nhập câu hỏi của bạn về chương trình GDPT...")
    if not question and st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("🔍 Đang tìm kiếm trong tài liệu và phân tích..."):
                answer, sources, docs_with_scores = _answer(
                    question,
                    debug_retrieval=st.session_state.debug_retrieval,
                )
            st.markdown(answer)
            if sources:
                with st.expander(f"📚 {len(sources)} tài liệu tham khảo"):
                    for src in sources:
                        st.markdown(_render_source_badge(src), unsafe_allow_html=True)

        st.session_state.messages.append({
            "role"   : "assistant",
            "content": answer,
            "sources": sources,
        })
        st.session_state.last_sources    = sources
        st.session_state.last_docs_with_scores = docs_with_scores
        st.session_state.total_questions += 1


with source_col:
    st.markdown("### 📚 Nguồn gần nhất")
    if st.session_state.last_sources:
        for i, src in enumerate(st.session_state.last_sources, 1):
            icon = file_icon(src.get("type", ""))
            href = src.get("url") or "#"
            name = src.get("name") or "Không rõ"
            page = src.get("page")
            cat  = src.get("category")
            bits = []
            if cat:  bits.append(str(cat))
            if page: bits.append(f"trang {page}")
            meta_line = " · ".join(bits)
            html = (
                f'<div class="stat-card">'
                f'<div class="label">Nguồn {i}</div>'
                f'<div class="value">{icon} <a href="{href}" target="_blank">{name}</a></div>'
            )
            if meta_line:
                html += f'<div class="meta">{meta_line}</div>'
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.caption("Nguồn tài liệu sẽ hiện sau câu trả lời đầu tiên.")

    if st.session_state.debug_retrieval and st.session_state.last_docs_with_scores:
        st.divider()
        st.markdown("### 🔍 Retrieval debug")
        rows = st.session_state.last_docs_with_scores
        csv_data = _docs_with_scores_to_csv(rows)
        st.download_button(
            "📥 Export retrieved chunks (CSV)",
            data=csv_data,
            file_name="retrieved_chunks.csv",
            mime="text/csv",
            use_container_width=True,
        )

        for i, row in enumerate(rows, start=1):
            score = row.get("score")
            score_txt = f"{score:.4f}" if isinstance(score, float) else "n/a"
            title = f"Chunk {i} · score={score_txt}"
            with st.expander(title):
                st.markdown(f"**Tài liệu:** {row.get('document_name')}")
                st.markdown(
                    f"- **Trang:** {row.get('page_number')}\n"
                    f"- **Chunk:** {row.get('chunk_index')}\n"
                    f"- **Độ dài:** {row.get('char_count')} ký tự"
                )
                src = row.get("source_url")
                if src:
                    st.markdown(f"[Nguồn]({src})")
                st.code(row.get("content_preview") or "", language="text")

    st.divider()
    st.markdown("### ⚡ Hỏi nhanh")
    quick_questions = [
        "Điều kiện lên lớp?",
        "Chương trình GDPT 2018?",
        "Đánh giá học sinh?",
        "Môn học bắt buộc THPT?",
        "Điều kiện tốt nghiệp?",
    ]
    for qq in quick_questions:
        if st.button(qq, key=f"quick_{qq}", use_container_width=True):
            st.session_state.pending_question = qq
            st.rerun()
