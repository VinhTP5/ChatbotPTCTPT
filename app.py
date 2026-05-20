"""
app.py
------
Streamlit app — Chatbot RAG đa nhà cung cấp LLM.

API key do dev tích hợp qua biến môi trường / Streamlit Secrets:
    GROQ_API_KEY        → Groq
    OPENAI_API_KEY      → OpenAI
    ANTHROPIC_API_KEY   → Anthropic Claude
    GOOGLE_API_KEY      → Google Gemini
    ADMIN_PASSWORD      → Mật khẩu đăng nhập admin panel

Người dùng cuối KHÔNG cần nhập API key. App tự phát hiện provider có sẵn.
"""

from __future__ import annotations

# Fix encoding UTF-8 trên Windows (Python 3.14 mặc định dùng cp1252)
import os as _os
_os.environ.setdefault("PYTHONUTF8", "1")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
import csv
import json
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

# Đường dẫn file lưu cấu hình admin
ADMIN_CONFIG_PATH = Path(__file__).resolve().parent / "admin_config.json"

import streamlit as st  # noqa: E402

from config import (  # noqa: E402
    CHROMA_DIR,
    CHUNKING_STRATEGIES,
    CHUNK_VARIANTS,
    DEFAULT_CATEGORIES,
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
    FAST_LOAD_COLLECTIONS,
    MAX_TOP_K,
    MIN_TOP_K,
    PROVIDERS,
    SEARCH_TYPES,
    SOURCE_CATEGORIES,
    build_collection_name,
    is_fast_load,
)
from llm_providers import (  # noqa: E402
    NoProviderConfiguredError,
    ProviderUnavailableError,
    available_providers,
    describe_status,
)
from rag_engine import load_rag_engine, list_available_collections  # noqa: E402


# ── Admin config: đọc/ghi file JSON ──────────────────────────────────────────

def _load_admin_config() -> dict:
    """Đọc cấu hình admin từ file; trả về defaults nếu chưa có."""
    defaults: dict = {
        "provider"          : "openai",
        "model"             : "gpt-4o",
        "embed_alias"       : DEFAULT_EMBED_ALIAS,
        "chunk_variant"     : DEFAULT_CHUNK_VARIANT,
        "chunking_strategy" : DEFAULT_CHUNKING_STRATEGY,
        "search_type"       : DEFAULT_SEARCH_TYPE,
        "top_k"             : DEFAULT_TOP_K,
        "fetch_k"           : DEFAULT_FETCH_K,
        "lambda_mult"       : DEFAULT_LAMBDA_MULT,
        "score_threshold"   : DEFAULT_SCORE_THRESHOLD,
        "temperature"       : DEFAULT_TEMPERATURE,
        "max_tokens"        : DEFAULT_MAX_TOKENS,
        "use_rerank"        : DEFAULT_USE_RERANK,
        "neighbor_k"        : DEFAULT_NEIGHBOR_K,
        "categories"        : list(DEFAULT_CATEGORIES),
    }
    try:
        if ADMIN_CONFIG_PATH.exists():
            with open(ADMIN_CONFIG_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception:
        pass
    return defaults


def _save_admin_config(cfg: dict) -> bool:
    """Ghi cấu hình admin vào file. Trả về True nếu thành công."""
    try:
        with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"❌ Không thể lưu cấu hình: {e}")
        return False


def _get_admin_password() -> str:
    """Lấy mật khẩu admin từ Streamlit Secrets hoặc biến môi trường."""
    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"]).strip()
    except Exception:
        pass
    return (_os.getenv("ADMIN_PASSWORD") or "").strip()


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
        margin-bottom: 0.7rem;
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

    /* ── Source selector bar ── */
    .source-bar {
        background: rgba(255,255,255,0.92);
        border: 1px solid var(--line-200);
        border-radius: 14px;
        padding: 0.55rem 1rem;
        margin-bottom: 0.65rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 2px 8px rgba(15,23,42,0.05);
    }
    .source-bar-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        white-space: nowrap;
        margin-right: 0.3rem;
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

    /* ── Admin badge ── */
    .admin-badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: #fef3c7; border: 1px solid #fcd34d; color: #92400e;
        border-radius: 20px; padding: 0.2rem 0.75rem;
        font-size: 0.75rem; font-weight: 600;
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


# ── Đọc admin config (mỗi lần reload đọc lại từ file) ────────────────────────
_admin_cfg = _load_admin_config()


# ── Session state init ────────────────────────────────────────────────────────
_DEFAULTS = {
    "messages"              : [],
    "engine"                : None,
    "doc_count"             : 0,
    "model_loaded"          : False,
    "selected_provider"     : None,
    "selected_model"        : None,
    # Nguồn tài liệu: lấy từ admin config (mặc định FPT on, Bộ GD off)
    "selected_categories"   : list(_admin_cfg.get("categories", DEFAULT_CATEGORIES)),
    "last_sources"          : [],
    "last_docs_with_scores" : [],
    "total_questions"       : 0,
    "selected_embed_alias"      : _admin_cfg.get("embed_alias", DEFAULT_EMBED_ALIAS),
    "selected_chunk_variant"    : _admin_cfg.get("chunk_variant", DEFAULT_CHUNK_VARIANT),
    "selected_chunking_strategy": _admin_cfg.get("chunking_strategy", DEFAULT_CHUNKING_STRATEGY),
    "debug_retrieval"       : False,
    "use_rerank"            : _admin_cfg.get("use_rerank", DEFAULT_USE_RERANK),
    "neighbor_k"            : _admin_cfg.get("neighbor_k", DEFAULT_NEIGHBOR_K),
    "auto_started"          : False,
    # Admin
    "admin_logged_in"       : False,
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


# ── Sidebar: Admin login + Panel cấu hình kỹ thuật ───────────────────────────
with st.sidebar:
    admin_pwd_configured = bool(_get_admin_password())

    # ── Khu vực đăng nhập admin ──
    if not st.session_state.admin_logged_in:
        st.markdown("## 🔐 Quản trị hệ thống")
        st.caption("Đăng nhập để truy cập panel cấu hình.")
        with st.form("admin_login_form", clear_on_submit=True):
            pwd_input = st.text_input("Mật khẩu:", type="password", label_visibility="collapsed",
                                      placeholder="Nhập mật khẩu admin...")
            login_btn = st.form_submit_button("Đăng nhập", use_container_width=True, type="primary")
            if login_btn:
                correct_pwd = _get_admin_password()
                if correct_pwd and pwd_input == correct_pwd:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                elif not correct_pwd:
                    st.error("⚠️ ADMIN_PASSWORD chưa được cài đặt.")
                else:
                    st.error("❌ Sai mật khẩu!")
    else:
        # ── Admin đã đăng nhập — hiện full config panel ──
        st.markdown(
            '<div class="admin-badge">🔑 Admin đã đăng nhập</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.divider()
        st.markdown("## ⚙️ Cấu hình hệ thống")
        st.caption("Thay đổi sẽ áp dụng cho tất cả người dùng sau khi lưu.")

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
            cfg_provider = _admin_cfg.get("provider", "openai")
            prov_idx = avail.index(cfg_provider) if cfg_provider in avail else 0
            selected_provider = st.selectbox(
                "Provider:", options=avail,
                format_func=lambda p: PROVIDERS[p]["label"],
                index=prov_idx, label_visibility="collapsed",
            )
            models = PROVIDERS[selected_provider]["models"]
            st.markdown('<div class="section-label" style="margin-top:0.7rem">Model</div>', unsafe_allow_html=True)
            cfg_model = _admin_cfg.get("model", "gpt-4o")
            model_keys = list(models.keys())
            model_idx  = model_keys.index(cfg_model) if cfg_model in model_keys else 0
            selected_model = st.selectbox(
                "Model:", options=model_keys,
                format_func=lambda x: models[x],
                index=model_idx, label_visibility="collapsed",
            )

        built = _built_matrix()

        # ── Embedding + badge Fast/On-demand ──────────────────────────────────
        st.markdown('<div class="section-label" style="margin-top:0.7rem">Embedding</div>', unsafe_allow_html=True)
        embed_options = sorted(built["embed"]) if built["embed"] else list(EMBED_MODELS.keys())
        cfg_embed = _admin_cfg.get("embed_alias", DEFAULT_EMBED_ALIAS)

        def _embed_label(x: str) -> str:
            """Hiển thị tên embedding kèm badge ⚡ (fast) hoặc 🔄 (on-demand)."""
            # Kiểm tra xem embed này có nằm trong ít nhất 1 fast-load collection không
            fast = any(c.startswith(x + "__") for c in FAST_LOAD_COLLECTIONS)
            badge = "⚡" if fast else "🔄"
            return f"{badge} {x} — {EMBED_MODELS[x]['label']}" if x in EMBED_MODELS else f"{badge} {x}"

        selected_embed_alias = st.selectbox(
            "Embedding:", options=embed_options,
            index=embed_options.index(cfg_embed) if cfg_embed in embed_options else 0,
            format_func=_embed_label,
            label_visibility="collapsed",
        )

        # ── Chunking ──────────────────────────────────────────────────────────
        st.markdown('<div class="section-label" style="margin-top:0.7rem">Chunking</div>', unsafe_allow_html=True)
        variant_options = sorted(built["variant"]) if built["variant"] else list(CHUNK_VARIANTS.keys())
        cfg_variant = _admin_cfg.get("chunk_variant", DEFAULT_CHUNK_VARIANT)
        selected_chunk_variant = st.selectbox(
            "Variant:", options=variant_options,
            index=variant_options.index(cfg_variant) if cfg_variant in variant_options else 0,
            format_func=lambda x: CHUNK_VARIANTS[x]["label"],
            label_visibility="collapsed",
        )
        strategy_options = sorted(built["strategy"]) if built["strategy"] else list(CHUNKING_STRATEGIES.keys())
        cfg_strategy = _admin_cfg.get("chunking_strategy", DEFAULT_CHUNKING_STRATEGY)
        selected_chunking_strategy = st.selectbox(
            "Strategy:", options=strategy_options,
            index=strategy_options.index(cfg_strategy) if cfg_strategy in strategy_options else 0,
            format_func=lambda x: CHUNKING_STRATEGIES[x],
            label_visibility="collapsed",
        )

        top_k = st.slider(
            "Top-K tài liệu:", min_value=MIN_TOP_K, max_value=MAX_TOP_K,
            value=int(_admin_cfg.get("top_k", DEFAULT_TOP_K)),
        )

        # Nâng cao
        with st.expander("⚙️ Nâng cao"):
            cfg_search = _admin_cfg.get("search_type", DEFAULT_SEARCH_TYPE)
            search_type = st.selectbox(
                "Search type", options=SEARCH_TYPES,
                index=SEARCH_TYPES.index(cfg_search) if cfg_search in SEARCH_TYPES else 0,
            )
            fetch_k = st.slider(
                "Fetch-K", min_value=top_k, max_value=50,
                value=max(int(_admin_cfg.get("fetch_k", DEFAULT_FETCH_K)), top_k), step=1,
            )
            lambda_mult = st.slider(
                "Lambda (MMR)", min_value=0.0, max_value=1.0,
                value=float(_admin_cfg.get("lambda_mult", DEFAULT_LAMBDA_MULT)), step=0.05,
                disabled=(search_type != "mmr"),
            )
            score_threshold = st.slider(
                "Score threshold", min_value=0.0, max_value=1.0,
                value=float(_admin_cfg.get("score_threshold") or 0.3), step=0.05,
                disabled=(search_type != "similarity_score_threshold"),
            )
            temperature = st.slider(
                "Temperature", min_value=0.0, max_value=1.0,
                value=float(_admin_cfg.get("temperature", DEFAULT_TEMPERATURE)), step=0.05,
            )
            max_tokens = st.slider(
                "Max tokens", min_value=256, max_value=8192,
                value=int(_admin_cfg.get("max_tokens", DEFAULT_MAX_TOKENS)), step=128,
            )
            debug_retrieval = st.checkbox(
                "🔍 Debug retrieval", value=st.session_state.debug_retrieval,
            )
            st.session_state.debug_retrieval = debug_retrieval

            use_rerank = st.toggle(
                "Reranker (BGE-M3)", value=bool(_admin_cfg.get("use_rerank", DEFAULT_USE_RERANK)),
                help="Chậm hơn ~2-3s nhưng chính xác hơn.",
            )
            neighbor_k = st.slider(
                "Neighbor context (±chunk)", min_value=0, max_value=3,
                value=int(_admin_cfg.get("neighbor_k", DEFAULT_NEIGHBOR_K)), step=1,
            )

        target_collection = build_collection_name(
            selected_embed_alias, selected_chunk_variant, selected_chunking_strategy,
        )
        collection_ready = target_collection in built["full"]
        _is_fast = is_fast_load(target_collection)
        if not collection_ready:
            st.warning("⚠️ Collection chưa có trong DB — cần build_db trước.")
        elif _is_fast:
            st.success(f"⚡ Fast-load: `{target_collection}`")
        else:
            st.info(
                f"🔄 On-demand: `{target_collection}`\n\n"
                "Collection này không nằm trong fast-load — sẽ tải khi bấm **Áp dụng**."
            )

        # Nguồn tài liệu mặc định (admin config)
        st.markdown('<div class="section-label" style="margin-top:0.7rem">Nguồn mặc định (tất cả người dùng)</div>',
                    unsafe_allow_html=True)
        admin_cats: list[str] = []
        cfg_cats = _admin_cfg.get("categories", DEFAULT_CATEGORIES)
        for cat_id, info in SOURCE_CATEGORIES.items():
            if st.checkbox(
                f"{info['icon']} {info['short']}",
                value=cat_id in cfg_cats,
                key=f"admin_cat_{cat_id}",
                help=info["description"],
            ):
                admin_cats.append(cat_id)
        if not admin_cats:
            st.warning("⚠️ Phải chọn ít nhất 1 nguồn.")

        st.divider()

        # ── Nút Lưu cấu hình ──
        col_save, col_apply = st.columns(2)
        with col_save:
            if st.button(
                "💾 Lưu cấu hình",
                type="primary",
                use_container_width=True,
                disabled=(selected_provider is None or not admin_cats or not collection_ready),
                help="Ghi cấu hình vào file — người dùng mới sẽ dùng cấu hình này.",
            ):
                new_cfg = {
                    "provider"          : selected_provider,
                    "model"             : selected_model,
                    "embed_alias"       : selected_embed_alias,
                    "chunk_variant"     : selected_chunk_variant,
                    "chunking_strategy" : selected_chunking_strategy,
                    "search_type"       : search_type,
                    "top_k"             : top_k,
                    "fetch_k"           : fetch_k,
                    "lambda_mult"       : lambda_mult,
                    "score_threshold"   : score_threshold,
                    "temperature"       : temperature,
                    "max_tokens"        : max_tokens,
                    "use_rerank"        : use_rerank,
                    "neighbor_k"        : neighbor_k,
                    "categories"        : admin_cats,
                }
                if _save_admin_config(new_cfg):
                    st.success("✅ Đã lưu!")
                    st.rerun()

        with col_apply:
            if st.button(
                "🚀 Áp dụng",
                use_container_width=True,
                disabled=(selected_provider is None or not admin_cats or not collection_ready),
                help="Khởi động lại engine với cấu hình hiện tại.",
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
                        categories=admin_cats,
                        use_rerank=use_rerank, neighbor_k=neighbor_k,
                    )
                if ok:
                    st.session_state.selected_categories = list(admin_cats)
                    st.session_state.selected_embed_alias = selected_embed_alias
                    st.session_state.selected_chunk_variant = selected_chunk_variant
                    st.session_state.selected_chunking_strategy = selected_chunking_strategy
                    st.session_state.use_rerank = use_rerank
                    st.session_state.neighbor_k = neighbor_k
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

    # ── Khi chưa đăng nhập: hiện nút xóa lịch sử (hữu ích cho user thường) ──
    if not st.session_state.admin_logged_in:
        st.divider()
        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            st.session_state.messages        = []
            st.session_state.last_sources    = []
            st.session_state.total_questions = 0
            st.rerun()
        if st.session_state.model_loaded:
            prov_lbl = PROVIDERS[st.session_state.selected_provider]["label"]
            st.markdown(f'<div class="status-online">🟢 {prov_lbl}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Vectors", f"{st.session_state.doc_count:,}")
            c2.metric("Câu hỏi", st.session_state.total_questions)


# ── Auto-start: tự khởi động khi mở app lần đầu ─────────────────────────────
# Chỉ auto-start với FAST_LOAD_COLLECTIONS (bge_m3__coarse hoặc minilm__coarse).
# Collections khác phải do admin bấm "Áp dụng" để load theo yêu cầu.
if not st.session_state.model_loaded and not st.session_state.auto_started:
    avail_now  = available_providers()
    built_now  = _built_matrix()
    if avail_now and built_now["full"]:
        # Ưu tiên provider/model từ admin config
        _prov_cfg = _admin_cfg.get("provider", "openai")
        _prov = _prov_cfg if _prov_cfg in avail_now else avail_now[0]
        _model_cfg = _admin_cfg.get("model", "gpt-4o")
        _models_list = list(PROVIDERS[_prov]["models"].keys())
        _model = _model_cfg if _model_cfg in _models_list else _models_list[0]

        _embed   = _admin_cfg.get("embed_alias", DEFAULT_EMBED_ALIAS)
        _variant = _admin_cfg.get("chunk_variant", DEFAULT_CHUNK_VARIANT)
        _strategy = _admin_cfg.get("chunking_strategy", DEFAULT_CHUNKING_STRATEGY)
        _target  = build_collection_name(_embed, _variant, _strategy)

        # ── Kiểm tra fast-load: nếu collection trong admin config KHÔNG phải
        #    fast-load, tìm fast-load collection tốt nhất để dùng thay thế.
        if not is_fast_load(_target) or _target not in built_now["full"]:
            # Duyệt theo thứ tự ưu tiên trong FAST_LOAD_COLLECTIONS
            _fast_target = next(
                (c for c in FAST_LOAD_COLLECTIONS if c in built_now["full"]),
                None,
            )
            if _fast_target:
                _parts = _fast_target.split("__")
                _embed, _variant, _strategy = _parts[0], _parts[1], _parts[2]
                _target = _fast_target
            else:
                # Không có fast-load nào trong DB → không auto-start
                st.session_state.auto_started = True
                _target = None  # type: ignore[assignment]

        if _target and _target in built_now["full"]:
            _cats = list(_admin_cfg.get("categories", DEFAULT_CATEGORIES))
            with st.spinner("⏳ Đang khởi động chatbot..."):
                _ok, _msg = _do_start_engine(
                    provider=_prov, model=_model,
                    top_k=int(_admin_cfg.get("top_k", DEFAULT_TOP_K)),
                    search_type=_admin_cfg.get("search_type", DEFAULT_SEARCH_TYPE),
                    fetch_k=int(_admin_cfg.get("fetch_k", DEFAULT_FETCH_K)),
                    lambda_mult=float(_admin_cfg.get("lambda_mult", DEFAULT_LAMBDA_MULT)),
                    score_threshold=_admin_cfg.get("score_threshold", DEFAULT_SCORE_THRESHOLD),
                    temperature=float(_admin_cfg.get("temperature", DEFAULT_TEMPERATURE)),
                    max_tokens=int(_admin_cfg.get("max_tokens", DEFAULT_MAX_TOKENS)),
                    embed_alias=_embed,
                    chunk_variant=_variant,
                    chunking_strategy=_strategy,
                    categories=_cats,
                    use_rerank=bool(_admin_cfg.get("use_rerank", DEFAULT_USE_RERANK)),
                    neighbor_k=int(_admin_cfg.get("neighbor_k", DEFAULT_NEIGHBOR_K)),
                )
            if _ok:
                st.session_state.selected_categories = _cats
                st.rerun()
            else:
                st.session_state.auto_started = True  # ngăn loop vô hạn


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


# ── Thanh chọn nguồn tài liệu (hiển thị cho tất cả người dùng) ───────────────
_cur_cats = st.session_state.selected_categories
_new_cats: list[str] = []

_src_cols = st.columns([1] + [1] * len(SOURCE_CATEGORIES) + [4])
with _src_cols[0]:
    st.markdown(
        '<div style="padding-top:0.45rem;font-size:0.75rem;font-weight:600;'
        'color:#64748b;text-transform:uppercase;letter-spacing:0.07em;">Nguồn:</div>',
        unsafe_allow_html=True,
    )
for _i, (_cat_id, _info) in enumerate(SOURCE_CATEGORIES.items()):
    with _src_cols[_i + 1]:
        _checked = st.toggle(
            f"{_info['icon']} {_info['short']}",
            value=(_cat_id in _cur_cats),
            key=f"src_toggle_{_cat_id}",
            help=_info["description"],
        )
        if _checked:
            _new_cats.append(_cat_id)

# Đảm bảo ít nhất 1 nguồn được chọn
if not _new_cats:
    _new_cats = list(_cur_cats) or list(SOURCE_CATEGORIES.keys())[:1]
    st.warning("⚠️ Cần chọn ít nhất 1 nguồn tài liệu.", icon="⚠️")

# Nếu nguồn thay đổi → cập nhật retrieval params ngay
if set(_new_cats) != set(_cur_cats):
    st.session_state.selected_categories = _new_cats
    if st.session_state.model_loaded and st.session_state.engine is not None:
        try:
            cats_arg_rt = (
                _new_cats if len(_new_cats) < len(SOURCE_CATEGORIES) else None
            )
            st.session_state.engine.set_retrieval_params(
                categories=cats_arg_rt,
            )
        except Exception:
            pass

st.markdown('<div class="chat-shell">', unsafe_allow_html=True)

# ── Màn hình chào (chỉ hiện khi chưa sẵn sàng) ───────────────────────────────
if not st.session_state.model_loaded:
    col1, col2, col3 = st.columns(3)
    cards = [
        ("1", "Đang khởi động", "Chatbot đang tải dữ liệu, vui lòng chờ..."),
        ("2", "Chọn nguồn",     "Bật/tắt nguồn tài liệu FPT hoặc Bộ GD&ĐT ở trên"),
        ("3", "Bắt đầu hỏi",   "Nhập câu hỏi vào ô bên dưới"),
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
    # Lịch sử hội thoại
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"📚 {len(msg['sources'])} tài liệu tham khảo", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(_render_source_badge(src), unsafe_allow_html=True)

    # Input ở cuối
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


# ── Cột phải: trạng thái + nguồn gần nhất ─────────────────────────────────────
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
        # Hiện nguồn đang dùng
        active_src_labels = [
            f"{SOURCE_CATEGORIES[c]['icon']} {SOURCE_CATEGORIES[c]['short']}"
            for c in st.session_state.selected_categories
            if c in SOURCE_CATEGORIES
        ]
        if active_src_labels:
            st.markdown(
                f'<div class="stat-chip" style="margin-top:0.35rem;font-size:0.72rem;">'
                f'📂 {" · ".join(active_src_labels)}</div>',
                unsafe_allow_html=True,
            )
    st.markdown("")

    # Nguồn gần nhất
    if st.session_state.last_sources:
        with st.expander(
            f"📚 Nguồn ({len(st.session_state.last_sources)})",
            expanded=False,
        ):
            for i, src in enumerate(st.session_state.last_sources, 1):
                st.markdown(_render_src_card(i, src), unsafe_allow_html=True)
    else:
        st.caption("📚 Nguồn tài liệu sẽ hiện ở đây sau câu trả lời đầu tiên.")

    # Debug retrieval (admin only)
    if st.session_state.admin_logged_in and st.session_state.debug_retrieval and st.session_state.last_docs_with_scores:
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
