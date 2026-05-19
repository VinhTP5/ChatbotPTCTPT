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

# Fix encoding UTF-8 trên Windows (Python 3.14 mặc định dùng cp1252)
import os as _os
_os.environ.setdefault("PYTHONUTF8", "1")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

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
        return

    parts = sorted(db_dir.glob("chroma.sqlite3.part.*"))
    if not parts:
        return

    print(f"[startup] Ghép {len(parts)} phần → chroma.sqlite3 ...", flush=True)
    with open(sqlite, "wb") as out:
        for part in parts:
            out.write(part.read_bytes())

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
    initial_sidebar_state="collapsed",   # sidebar ẩn mặc định
)

# ── CSS hiện đại ──────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    :root {
        --cmd-blue-900: #0a1f44;
        --cmd-blue-800: #123a7a;
        --cmd-blue-700: #1d4ed8;
        --cmd-blue-600: #2563eb;
        --cmd-blue-500: #3b82f6;
        --cmd-blue-100: #dbeafe;
        --cmd-blue-050: #eff6ff;
        --ink-900: #0f172a;
        --ink-700: #334155;
        --ink-500: #64748b;
        --line-200: #e2e8f0;
        --line-100: #eef2f7;
        --surface: #ffffff;
    }

    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background:
          radial-gradient(circle at 10% -10%, rgba(37,99,235,0.16), transparent 35%),
          radial-gradient(circle at 90% 0%, rgba(56,189,248,0.14), transparent 30%),
          linear-gradient(180deg, #f5f9ff 0%, #f8fbff 36%, #ffffff 100%);
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image:
          linear-gradient(rgba(148, 163, 184, 0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(148, 163, 184, 0.05) 1px, transparent 1px);
        background-size: 24px 24px;
        mask-image: radial-gradient(circle at center, black 50%, transparent 90%);
        z-index: 0;
    }

    .block-container {
        max-width: 1240px;
        padding-top: 1.2rem;
        position: relative;
        z-index: 1;
    }

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, var(--cmd-blue-900) 0%, var(--cmd-blue-800) 48%, var(--cmd-blue-600) 100%);
        color: white;
        padding: 1.15rem 1.8rem;
        border-radius: 18px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(13, 74, 166, 0.24);
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute; top: -40%; left: -10%;
        width: 60%; height: 200%;
        background: radial-gradient(ellipse, rgba(255,255,255,0.07) 0%, transparent 70%);
        pointer-events: none;
    }
    .main-header h1 {
        margin: 0; font-size: 1.55rem; font-weight: 700; letter-spacing: -0.01em;
    }
    .main-header p { margin: 0.3rem 0 0; opacity: 0.82; font-size: 0.88rem; }
    .header-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 999px;
        padding: 0.2rem 0.8rem;
        font-size: 0.75rem;
        margin-top: 0.5rem;
    }

    /* ── Khu vực chat trung tâm ── */
    .chat-shell {
        border: 1px solid var(--line-200);
        border-radius: 18px;
        background: rgba(255,255,255,0.88);
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
        padding: 0.85rem;
        margin-bottom: 0.65rem;
    }

    [data-testid="stVerticalBlock"]:has(> [data-testid="stChatMessage-user"]),
    [data-testid="stVerticalBlock"]:has(> [data-testid="stChatMessage-assistant"]) {
        width: 100%;
    }

    .stChatMessage {
        border-radius: 18px !important;
        margin-bottom: 0.6rem !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06) !important;
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
    }
    [data-testid="stChatMessage-user"] {
        background: linear-gradient(135deg, var(--cmd-blue-050), var(--cmd-blue-100)) !important;
        border: 1px solid #bfdbfe !important;
    }
    [data-testid="stChatMessage-assistant"] {
        background: var(--surface) !important;
        border: 1px solid var(--line-100) !important;
    }

    /* ── Chat input ── */
    [data-testid="stChatInput"] > div {
        border-radius: 16px !important;
        border: 2px solid var(--cmd-blue-600) !important;
        background: #ffffff !important;
        box-shadow: 0 6px 22px rgba(37,99,235,0.14) !important;
        transition: box-shadow 0.2s;
    }
    [data-testid="stChatInput"] > div:focus-within {
        box-shadow: 0 10px 26px rgba(37,99,235,0.24) !important;
    }
    [data-testid="stChatInput"] textarea {
        font-size: 0.95rem !important;
    }

    /* ── Source card (cột phải) ── */
    .src-card {
        background: #ffffff;
        border: 1px solid var(--line-200);
        border-left: 3px solid var(--cmd-blue-600);
        border-radius: 12px;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.4rem;
        font-size: 0.82rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        transition: box-shadow 0.15s;
    }
    .src-card:hover { box-shadow: 0 3px 10px rgba(37,99,235,0.10); }
    .src-card .src-title {
        font-weight: 600; color: #1e3a8a; font-size: 0.82rem; line-height: 1.3;
    }
    .src-card .src-meta { color: #64748b; font-size: 0.73rem; margin-top: 0.15rem; }
    .src-card a { color: var(--cmd-blue-600); text-decoration: none; }
    .src-card a:hover { text-decoration: underline; }

    /* ── Source badge trong chat ── */
    .source-item {
        background: #f2f8ff;
        border: 1px solid #c7dcff;
        border-radius: 8px;
        padding: 0.4rem 0.65rem;
        margin: 0.2rem 0;
        font-size: 0.84rem;
    }
    .source-item .small { color: #64748b; font-size: 0.75rem; }

    /* ── Stat chip ── */
    .stat-chip {
        display: inline-flex; align-items: center; gap: 0.3rem;
        background: #f8fbff; border: 1px solid #dbeafe; border-radius: 999px;
        padding: 0.2rem 0.7rem; font-size: 0.78rem; color: #1e3a8a; font-weight: 600;
    }

    .rail-panel {
        border: 1px solid var(--line-200);
        border-radius: 14px;
        background: rgba(255,255,255,0.9);
        padding: 0.8rem;
    }

    /* ── Status badge ── */
    .status-online {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: #dcfce7; border: 1px solid #bbf7d0; color: #166534;
        border-radius: 20px; padding: 0.2rem 0.8rem;
        font-size: 0.78rem; font-weight: 600;
    }
    .status-offline {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: #fef2f2; border: 1px solid #fecaca; color: #991b1b;
        border-radius: 20px; padding: 0.2rem 0.8rem;
        font-size: 0.78rem; font-weight: 600;
    }

    /* ── Welcome cards ── */
    .welcome-card {
        background: linear-gradient(135deg, #f7fbff, #eef5ff);
        border: 1px solid #dbeafe; border-radius: 14px;
        padding: 1.1rem 1.2rem; text-align: center;
    }
    .welcome-card .step-num {
        background: #2563eb; color: white;
        width: 28px; height: 28px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 0.8rem; font-weight: 700; margin-bottom: 0.4rem;
    }
    .welcome-card .step-title { font-weight: 600; font-size: 0.9rem; color: #1e3a8a; }
    .welcome-card .step-desc  { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .stButton > button { border-radius: 10px; font-weight: 500; }

    /* ── Section label ── */
    .section-label {
        font-size: 0.72rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.08em;
        color: #94a3b8; margin-bottom: 0.3rem;
    }

    /* ── Misc ── */
    .stSpinner > div { border-top-color: var(--cmd-blue-600) !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
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
    "messages"              : [],
    "engine"                : None,
    "doc_count"             : 0,
    "model_loaded"          : False,
    "selected_provider"     : None,
    "selected_model"        : None,
    "selected_categories"   : list(SOURCE_CATEGORIES.keys()),
    "last_sources"          : [],
    "last_docs_with_scores" : [],
    "total_questions"       : 0,
    "selected_embed_alias"      : DEFAULT_EMBED_ALIAS,
    "selected_chunk_variant"    : DEFAULT_CHUNK_VARIANT,
    "selected_chunking_strategy": DEFAULT_CHUNKING_STRATEGY,
    "debug_retrieval"       : False,
    "use_rerank"            : DEFAULT_USE_RERANK,
    "neighbor_k"            : DEFAULT_NEIGHBOR_K,
    "auto_started"          : False,
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _answer(question: str, debug_retrieval: bool = False) -> tuple[str, list[dict], list[dict]]:
    try:
        if debug_retrieval:
            result = st.session_state.engine.ask_with_scores(question)
        else:
            result = st.session_state.engine.ask(question)
        return result.answer, result.sources, result.docs_with_scores
    except Exception as e:
        return f"❌ Lỗi khi xử lý câu hỏi: {e}", [], []


def _render_source_badge(src: dict) -> str:
    icon      = file_icon(src.get("type", ""))
    page      = src.get("page")
    cat       = src.get("category")
    size      = src.get("file_size_kb")
    bits = []
    if cat:  bits.append(str(cat))
    if page: bits.append(f"trang {page}")
    if size: bits.append(f"{size} KB")
    meta      = " · ".join(bits)
    view_href = src.get("url") or "#"
    raw_href  = src.get("raw_url") or view_href
    name      = src.get("name") or "Không rõ"
    return (
        f'<div class="source-item">{icon} '
        f'<a href="{view_href}" target="_blank" title="Xem trên GitHub">{name}</a>'
        f' &nbsp;·&nbsp; <a href="{raw_href}" target="_blank" title="Tải file gốc">⬇️</a>'
        + (f'<div class="small">{meta}</div>' if meta else "")
        + "</div>"
    )


def _render_src_card(i: int, src: dict) -> str:
    icon     = file_icon(src.get("type", ""))
    href     = src.get("url") or "#"
    raw_href = src.get("raw_url") or href
    name     = src.get("name") or "Không rõ"
    page     = src.get("page")
    cat      = src.get("category")
    bits = []
    if cat:  bits.append(str(cat))
    if page: bits.append(f"tr.{page}")
    meta = " · ".join(bits)
    return (
        f'<div class="src-card">'
        f'<div class="src-title">{icon} '
        f'<a href="{href}" target="_blank">{name}</a>'
        f' <a href="{raw_href}" target="_blank" style="font-size:0.7rem;color:#94a3b8;">⬇️</a></div>'
        + (f'<div class="src-meta">{meta}</div>' if meta else "")
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
        "embed"   : {p[0] for p in parsed},
        "variant" : {p[1] for p in parsed},
        "strategy": {p[2] for p in parsed},
        "full"    : {"__".join(p) for p in parsed},
    }


def _docs_with_scores_to_csv(rows: list[dict]) -> str:
    buf = StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["score","document_name","page_number","chunk_index",
                    "char_count","source_url","content_preview"],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "score"          : r.get("score"),
            "document_name"  : r.get("document_name"),
            "page_number"    : r.get("page_number"),
            "chunk_index"    : r.get("chunk_index"),
            "char_count"     : r.get("char_count"),
            "source_url"     : r.get("source_url"),
            "content_preview": r.get("content_preview"),
        })
    return buf.getvalue()


def _do_start_engine(
    provider, model, top_k, search_type, fetch_k,
    lambda_mult, score_threshold, temperature, max_tokens,
    embed_alias, chunk_variant, chunking_strategy,
    categories, use_rerank, neighbor_k,
) -> tuple[bool, str]:
    """Khởi động RAG engine. Trả về (success, message)."""
    try:
        cats_arg = (
            categories
            if len(categories) < len(SOURCE_CATEGORIES)
            else None
        )
        engine, _retriever, doc_count = load_rag_engine(
            provider          = provider,
            model_name        = model,
            top_k             = top_k,
            search_type       = search_type,
            fetch_k           = fetch_k,
            lambda_mult       = lambda_mult,
            score_threshold   = score_threshold if search_type == "similarity_score_threshold" else None,
            temperature       = temperature,
            max_tokens        = max_tokens,
            embed_alias       = embed_alias,
            chunk_variant     = chunk_variant,
            chunking_strategy = chunking_strategy,
            categories        = cats_arg,
            use_rerank        = use_rerank,
            neighbor_k        = neighbor_k,
        )
        st.session_state.engine            = engine
        st.session_state.doc_count         = doc_count
        st.session_state.model_loaded      = True
        st.session_state.selected_provider = provider
        st.session_state.selected_model    = model
        st.session_state.messages          = []
        st.session_state.auto_started      = True
        return True, f"✅ Sẵn sàng! ({doc_count:,} vectors)"
    except FileNotFoundError as e:
        return False, f"❌ {e}"
    except (NoProviderConfiguredError, ProviderUnavailableError) as e:
        return False, f"❌ Cấu hình LLM: {e}"
    except Exception as e:
        return False, f"❌ Lỗi: {e}"


# ── Sidebar (collapsed mặc định) ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Cài đặt")

    # Provider
    st.markdown('<div class="section-label">Nhà cung cấp LLM</div>', unsafe_allow_html=True)
    avail = available_providers()
    if not avail:
        st.error(
            "Chưa có API key. Cần thiết lập: "
            + ", ".join(info["env_keys"][0] for info in PROVIDERS.values())
        )
        selected_provider = None
        selected_model    = None
    else:
        selected_provider = st.selectbox(
            "Provider:", options=avail,
            format_func=lambda p: PROVIDERS[p]["label"],
            index=0, label_visibility="collapsed",
        )
        models = PROVIDERS[selected_provider]["models"]
        st.markdown('<div class="section-label" style="margin-top:0.7rem">Model</div>', unsafe_allow_html=True)
        selected_model = st.selectbox(
            "Model:", options=list(models.keys()),
            format_func=lambda x: models[x],
            index=0, label_visibility="collapsed",
        )

    built = _built_matrix()

    # Embedding
    st.markdown('<div class="section-label" style="margin-top:0.7rem">Embedding</div>', unsafe_allow_html=True)
    embed_options = sorted(built["embed"]) if built["embed"] else list(EMBED_MODELS.keys())
    selected_embed_alias = st.selectbox(
        "Embedding:", options=embed_options,
        index=embed_options.index(st.session_state.selected_embed_alias)
              if st.session_state.selected_embed_alias in embed_options else 0,
        format_func=lambda x: f"{x} — {EMBED_MODELS[x]['label']}",
        label_visibility="collapsed",
    )
    st.session_state.selected_embed_alias = selected_embed_alias

    # Chunking
    st.markdown('<div class="section-label" style="margin-top:0.7rem">Chunking</div>', unsafe_allow_html=True)
    variant_options = sorted(built["variant"]) if built["variant"] else list(CHUNK_VARIANTS.keys())
    selected_chunk_variant = st.selectbox(
        "Variant:", options=variant_options,
        index=variant_options.index(st.session_state.selected_chunk_variant)
              if st.session_state.selected_chunk_variant in variant_options else 0,
        format_func=lambda x: CHUNK_VARIANTS[x]["label"],
        label_visibility="collapsed",
    )
    strategy_options = sorted(built["strategy"]) if built["strategy"] else list(CHUNKING_STRATEGIES.keys())
    selected_chunking_strategy = st.selectbox(
        "Strategy:", options=strategy_options,
        index=strategy_options.index(st.session_state.selected_chunking_strategy)
              if st.session_state.selected_chunking_strategy in strategy_options else 0,
        format_func=lambda x: CHUNKING_STRATEGIES[x],
        label_visibility="collapsed",
    )
    st.session_state.selected_chunk_variant     = selected_chunk_variant
    st.session_state.selected_chunking_strategy = selected_chunking_strategy

    top_k = st.slider(
        "Top-K tài liệu:", min_value=MIN_TOP_K, max_value=MAX_TOP_K, value=DEFAULT_TOP_K,
    )

    # Nguồn tài liệu
    st.markdown('<div class="section-label" style="margin-top:0.7rem">Nguồn tài liệu</div>', unsafe_allow_html=True)
    selected_categories: list[str] = []
    for cat_id, info in SOURCE_CATEGORIES.items():
        if st.checkbox(
            f"{info['icon']} {info['short']}",
            value=cat_id in st.session_state.selected_categories,
            key=f"cat_{cat_id}",
            help=info["description"],
        ):
            selected_categories.append(cat_id)
    st.session_state.selected_categories = selected_categories
    if not selected_categories:
        st.warning("⚠️ Phải chọn ít nhất 1 nguồn.")

    # Nâng cao
    with st.expander("⚙️ Nâng cao"):
        search_type = st.selectbox(
            "Search type", options=SEARCH_TYPES,
            index=SEARCH_TYPES.index(DEFAULT_SEARCH_TYPE) if DEFAULT_SEARCH_TYPE in SEARCH_TYPES else 0,
        )
        fetch_k = st.slider(
            "Fetch-K", min_value=top_k, max_value=50,
            value=max(DEFAULT_FETCH_K, top_k), step=1,
        )
        lambda_mult = st.slider(
            "Lambda (MMR)", min_value=0.0, max_value=1.0,
            value=float(DEFAULT_LAMBDA_MULT), step=0.05,
            disabled=(search_type != "mmr"),
        )
        score_threshold = st.slider(
            "Score threshold", min_value=0.0, max_value=1.0,
            value=float(DEFAULT_SCORE_THRESHOLD or 0.3), step=0.05,
            disabled=(search_type != "similarity_score_threshold"),
        )
        temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0,
            value=DEFAULT_TEMPERATURE, step=0.05,
        )
        max_tokens = st.slider(
            "Max tokens", min_value=256, max_value=8192,
            value=DEFAULT_MAX_TOKENS, step=128,
        )
        debug_retrieval = st.checkbox(
            "🔍 Debug retrieval", value=st.session_state.debug_retrieval,
        )
        st.session_state.debug_retrieval = debug_retrieval

        use_rerank = st.toggle(
            "Reranker (BGE-M3)", value=st.session_state.use_rerank,
            help="Chậm hơn ~2-3s nhưng chính xác hơn.",
        )
        st.session_state.use_rerank = use_rerank

        neighbor_k = st.slider(
            "Neighbor context (±chunk)", min_value=0, max_value=3,
            value=st.session_state.neighbor_k, step=1,
        )
        st.session_state.neighbor_k = neighbor_k

    target_collection = build_collection_name(
        selected_embed_alias, selected_chunk_variant, selected_chunking_strategy,
    )
    collection_ready = target_collection in built["full"]
    if not collection_ready:
        st.warning("⚠️ Collection chưa có trong DB — cần build_db trước.")

    st.divider()

    # Cập nhật retrieval params runtime
    if (
        st.session_state.model_loaded
        and st.session_state.engine is not None
        and selected_categories
    ):
        try:
            cats_arg_rt = (
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
                categories=cats_arg_rt,
                use_rerank=use_rerank,
                neighbor_k=neighbor_k,
            )
        except Exception:
            pass

    btn_label = "🔄 Khởi động lại" if st.session_state.model_loaded else "🚀 Khởi động"
    if st.button(
        btn_label, type="primary", use_container_width=True,
        disabled=(selected_provider is None or not selected_categories or not collection_ready),
    ):
        with st.spinner("Đang tải mô hình..."):
            ok, msg = _do_start_engine(
                provider=selected_provider, model=selected_model,
                top_k=top_k, search_type=search_type, fetch_k=fetch_k,
                lambda_mult=lambda_mult, score_threshold=score_threshold,
                temperature=temperature, max_tokens=max_tokens,
                embed_alias=selected_embed_alias,
                chunk_variant=selected_chunk_variant,
                chunking_strategy=selected_chunking_strategy,
                categories=selected_categories,
                use_rerank=use_rerank, neighbor_k=neighbor_k,
            )
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # Thống kê
    st.markdown('<div class="section-label">Trạng thái</div>', unsafe_allow_html=True)
    if st.session_state.model_loaded:
        prov_lbl  = PROVIDERS[st.session_state.selected_provider]["label"]
        model_lbl = st.session_state.selected_model or ""
        st.markdown(f'<div class="status-online">🟢 {prov_lbl}</div>', unsafe_allow_html=True)
        st.caption(f"Model: `{model_lbl}`")
        if st.session_state.engine:
            st.caption(f"Collection: `{st.session_state.engine.collection_name}`")
        c1, c2 = st.columns(2)
        c1.metric("Vectors", f"{st.session_state.doc_count:,}")
        c2.metric("Câu hỏi", st.session_state.total_questions)
    else:
        st.markdown('<div class="status-offline">🔴 Chưa khởi động</div>', unsafe_allow_html=True)

    db_exists = Path(CHROMA_DIR).exists() and any(Path(CHROMA_DIR).iterdir())
    st.caption("✅ Database: sẵn sàng" if db_exists else "❌ Database: chưa có")

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages        = []
        st.session_state.last_sources    = []
        st.session_state.total_questions = 0
        st.rerun()

    with st.expander("🩺 Trạng thái hệ thống"):
        st.code(describe_status(), language="text")


# ── Auto-start: tự khởi động khi mở app lần đầu ─────────────────────────────
if not st.session_state.model_loaded and not st.session_state.auto_started:
    avail_now = available_providers()
    built_now  = _built_matrix()
    if avail_now and built_now["full"]:
        _prov  = avail_now[0]
        _model = list(PROVIDERS[_prov]["models"].keys())[0]
        _embed = (
            st.session_state.selected_embed_alias
            if st.session_state.selected_embed_alias in built_now["embed"]
            else sorted(built_now["embed"])[0]
        )
        _variant = (
            st.session_state.selected_chunk_variant
            if st.session_state.selected_chunk_variant in built_now["variant"]
            else sorted(built_now["variant"])[0]
        )
        _strategy = (
            st.session_state.selected_chunking_strategy
            if st.session_state.selected_chunking_strategy in built_now["strategy"]
            else sorted(built_now["strategy"])[0]
        )
        _target = build_collection_name(_embed, _variant, _strategy)
        if _target in built_now["full"]:
            with st.spinner("⏳ Đang khởi động chatbot..."):
                _ok, _msg = _do_start_engine(
                    provider=_prov, model=_model,
                    top_k=DEFAULT_TOP_K,
                    search_type=DEFAULT_SEARCH_TYPE,
                    fetch_k=DEFAULT_FETCH_K,
                    lambda_mult=DEFAULT_LAMBDA_MULT,
                    score_threshold=DEFAULT_SCORE_THRESHOLD,
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    embed_alias=_embed,
                    chunk_variant=_variant,
                    chunking_strategy=_strategy,
                    categories=list(SOURCE_CATEGORIES.keys()),
                    use_rerank=DEFAULT_USE_RERANK,
                    neighbor_k=DEFAULT_NEIGHBOR_K,
                )
            if _ok:
                st.rerun()
            else:
                st.session_state.auto_started = True   # ngăn loop vô hạn


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
    <h1>🎓 Chatbot Tư Vấn Giáo Dục Phổ Thông</h1>
    <p>Hỏi đáp thông minh dựa trên văn bản quy định của Bộ GD&amp;ĐT &amp; FPT/FSC</p>
    <span class="header-badge">CT GDPT 2018 · TT 32/2018 · Quyết định FPT/FSC</span>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="chat-shell">', unsafe_allow_html=True)

# ── Màn hình chào (chỉ hiện khi chưa sẵn sàng) ───────────────────────────────
if not st.session_state.model_loaded:
    col1, col2, col3 = st.columns(3)
    cards = [
        ("1", "Mở cài đặt",  "Click ☰ để mở sidebar, chọn LLM provider"),
        ("2", "Chọn model",  "Chọn provider và model phù hợp"),
        ("3", "Bắt đầu hỏi","Nhập câu hỏi vào ô bên dưới"),
    ]
    for col, (num, title, desc) in zip([col1, col2, col3], cards):
        with col:
            st.markdown(
                f'<div class="welcome-card">'
                f'<div class="step-num">{num}</div>'
                f'<div class="step-title">{title}</div>'
                f'<div class="step-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.markdown("---")
    st.markdown("##### 💡 Câu hỏi ví dụ")
    ex_cols = st.columns(2)
    examples = [
        "Học sinh cần đáp ứng điều kiện gì để được lên lớp?",
        "Cấu trúc chương trình GDPT 2018 gồm những gì?",
        "Quy định về đánh giá học sinh tiểu học như thế nào?",
        "Các môn học bắt buộc ở cấp THPT là gì?",
        "Điều kiện tốt nghiệp THPT theo quy định hiện hành?",
        "Kế hoạch giáo dục FSC năm 2026-2027 có điểm gì mới?",
    ]
    for i, ex in enumerate(examples):
        with ex_cols[i % 2]:
            st.markdown(f"- *{ex}*")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ── Layout chính: chat (3) | nguồn (1) ───────────────────────────────────────
chat_col, source_col = st.columns([3, 1])

with chat_col:
    # Lịch sử hội thoại đẩy lên trên, input pin dưới
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"📚 {len(msg['sources'])} tài liệu tham khảo", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(_render_source_badge(src), unsafe_allow_html=True)

    # Input ở cuối (Streamlit tự pin xuống)
    question = st.chat_input("Nhập câu hỏi về chương trình GDPT, quy định FPT/FSC...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("🔍 Đang phân tích tài liệu..."):
                model_before = getattr(st.session_state.engine, "model", st.session_state.selected_model)
                answer, sources, docs_with_scores = _answer(
                    question,
                    debug_retrieval=st.session_state.debug_retrieval,
                )
                model_after = getattr(st.session_state.engine, "model", model_before)
            st.markdown(answer)
            if model_after != model_before:
                st.info(f"⚠️ Đã tự động fallback model: `{model_before}` → `{model_after}`")
                st.session_state.selected_model = model_after
            if sources:
                with st.expander(f"📚 {len(sources)} tài liệu tham khảo", expanded=False):
                    for src in sources:
                        st.markdown(_render_source_badge(src), unsafe_allow_html=True)

        st.session_state.messages.append({
            "role"   : "assistant",
            "content": answer,
            "sources": sources,
        })
        st.session_state.last_sources          = sources
        st.session_state.last_docs_with_scores = docs_with_scores
        st.session_state.total_questions      += 1


# ── Cột phải: trạng thái + nguồn gần nhất (thu gọn) ─────────────────────────
with source_col:
    st.markdown('<div class="rail-panel">', unsafe_allow_html=True)
    if st.session_state.model_loaded:
        prov_short = PROVIDERS[st.session_state.selected_provider]["label"]
        st.markdown(
            f'<div class="stat-chip">🟢 {prov_short}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="stat-chip" style="margin-top:0.35rem">💬 {st.session_state.total_questions} câu hỏi</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")

    # Nguồn gần nhất — accordion, mặc định đóng
    if st.session_state.last_sources:
        with st.expander(
            f"📚 Nguồn ({len(st.session_state.last_sources)})",
            expanded=False,
        ):
            for i, src in enumerate(st.session_state.last_sources, 1):
                st.markdown(_render_src_card(i, src), unsafe_allow_html=True)
    else:
        st.caption("📚 Nguồn tài liệu sẽ hiện ở đây sau câu trả lời đầu tiên.")

    # Debug retrieval (ẩn trong expander)
    if st.session_state.debug_retrieval and st.session_state.last_docs_with_scores:
        st.divider()
        with st.expander("🔍 Debug retrieval", expanded=False):
            rows = st.session_state.last_docs_with_scores
            st.download_button(
                "📥 Export CSV",
                data=_docs_with_scores_to_csv(rows),
                file_name="retrieved_chunks.csv",
                mime="text/csv",
                use_container_width=True,
            )
            for i, row in enumerate(rows, start=1):
                score     = row.get("score")
                score_txt = f"{score:.4f}" if isinstance(score, float) else "n/a"
                with st.expander(f"Chunk {i} · {score_txt}", expanded=False):
                    st.markdown(f"**{row.get('document_name')}**")
                    st.caption(
                        f"Trang {row.get('page_number')} · "
                        f"Chunk {row.get('chunk_index')} · "
                        f"{row.get('char_count')} ký tự"
                    )
                    if row.get("source_url"):
                        st.markdown(f"[Nguồn]({row['source_url']})")
                    st.code(row.get("content_preview") or "", language="text")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
