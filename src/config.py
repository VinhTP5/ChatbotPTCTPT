"""
config.py
---------
Cấu hình tập trung cho toàn hệ thống Chatbot PTCT PT.

Mọi cấu hình (provider, model, đường dẫn DB, chunking, metadata...) được tập trung
ở đây để dev dễ tích hợp và mở rộng. API key KHÔNG được hard-code trong file này
mà được đọc tự động từ biến môi trường (.env / Streamlit secrets / OS env).

Thứ tự ưu tiên đọc API key:
    1. Streamlit Secrets (khi deploy trên Streamlit Cloud)
    2. Biến môi trường OS / file .env
    3. None (provider tương ứng sẽ bị disable)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ── Load biến môi trường từ .env (nếu có) ─────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    # python-dotenv không bắt buộc — vẫn đọc được từ OS env
    pass


# ── Đường dẫn (cấu trúc thư mục mới) ──────────────────────────────────────────
# src/ chứa file này → PROJECT_ROOT là thư mục cha của src
SRC_DIR        = Path(__file__).resolve().parent
PROJECT_ROOT   = SRC_DIR.parent
DATA_DIR       = PROJECT_ROOT / "data"          # tài liệu nguồn
CHROMA_DIR     = str(PROJECT_ROOT / "chroma_db")  # vector chunks
DOCS_DIR       = str(DATA_DIR)                  # nguồn để index
INDEX_REGISTRY = str(PROJECT_ROOT / "chroma_db" / "indexed_files.json")


# ── Embedding models (chạy local, không cần API key) ─────────────────────────
EMBED_MODELS: dict[str, dict[str, str]] = {
    "minilm": {
        "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "label": "MiniLM-L12 (baseline)",
    },
    "mpnet": {
        "name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "label": "MPNet multilingual base",
    },
    "e5_base": {
        "name": "intfloat/multilingual-e5-base",
        "label": "E5 multilingual base",
    },
    "e5_large": {
        "name": "intfloat/multilingual-e5-large",
        "label": "E5 multilingual large",
    },
    "bge_m3": {
        "name": "BAAI/bge-m3",
        "label": "BGE-M3",
    },
}

DEFAULT_EMBED_ALIAS = "minilm"
EMBED_MODEL = EMBED_MODELS[DEFAULT_EMBED_ALIAS]["name"]


# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_VARIANTS = {
    "fine": {
        "chunk_size": 256,
        "chunk_overlap": 128,
        "label": "Fine — 256/128",
    },
    "balanced": {
        "chunk_size": 800,
        "chunk_overlap": 200,
        "label": "Balanced — 800/200",
    },
    "coarse": {
        "chunk_size": 1000,
        "chunk_overlap": 150,
        "label": "Coarse — 1000/150",
    },
}
DEFAULT_CHUNK_VARIANT = "coarse"

CHUNKING_STRATEGIES = {
    "standard": "Standard — embed từng chunk độc lập",
    "late": "Late Chunking — embed full text rồi pool theo chunk",
    "long_late": "Long Late Chunking — overlap windows cho tài liệu dài",
}
DEFAULT_CHUNKING_STRATEGY = "standard"

CHUNK_SIZE = CHUNK_VARIANTS[DEFAULT_CHUNK_VARIANT]["chunk_size"]
CHUNK_OVERLAP = CHUNK_VARIANTS[DEFAULT_CHUNK_VARIANT]["chunk_overlap"]
BATCH_SIZE = 500

DEFAULT_WINDOW_TOKENS = 512
DEFAULT_WINDOW_OVERLAP = 64


# ── Source URL — trỏ tới GitHub blob để xem tài liệu online ──────────────────
# Mặc định trỏ về repo của user; dev có thể override qua biến môi trường.
GITHUB_OWNER  = os.getenv("CHATBOT_GH_OWNER",  "VinhTP5")
GITHUB_REPO   = os.getenv("CHATBOT_GH_REPO",   "ChatbotPTCTPT")
GITHUB_BRANCH = os.getenv("CHATBOT_GH_BRANCH", "main")
# Thư mục con trong repo chứa tài liệu (tương đối)
GITHUB_DATA_PREFIX = os.getenv("CHATBOT_GH_DATA_PREFIX", "data")

# Có thể override toàn bộ domain (chuỗi base) qua biến môi trường nếu cần
DEFAULT_DOMAIN = os.getenv(
    "CHATBOT_DOC_DOMAIN",
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{GITHUB_DATA_PREFIX}",
)
# URL "raw" — dùng khi cần tải trực tiếp file (không xem qua GitHub UI)
RAW_DOMAIN = os.getenv(
    "CHATBOT_DOC_RAW_DOMAIN",
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_DATA_PREFIX}",
)


# ── Retrieval ─────────────────────────────────────────────────────────────────
DEFAULT_TOP_K = 5
MIN_TOP_K = 2
MAX_TOP_K = 10
SEARCH_TYPES = ["similarity", "mmr", "similarity_score_threshold"]
DEFAULT_SEARCH_TYPE = "mmr"
DEFAULT_FETCH_K = 20
DEFAULT_LAMBDA_MULT = 0.5
DEFAULT_SCORE_THRESHOLD: Optional[float] = None
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS  = 2048


# ── File formats được hỗ trợ ──────────────────────────────────────────────────
# Chỉ index các định dạng có nội dung phong phú. Các định dạng plain-text dạng
# bảng / markup (.csv, .doc, .html, .htm, .md) bị loại ra vì thường gây nhiễu
# khi chunking và không cải thiện chất lượng retrieval.
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx", ".xls",
    ".pptx", ".ppt",
    ".txt",
}


# ── Ngôn ngữ mặc định cho metadata ───────────────────────────────────────────
DEFAULT_LANGUAGE = "vi"


# ── Helper đọc secret an toàn ────────────────────────────────────────────────

def _get_secret(name: str) -> Optional[str]:
    """
    Đọc secret theo thứ tự ưu tiên:
        1. Streamlit Secrets (nếu Streamlit đang chạy)
        2. Biến môi trường (gồm cả .env đã load)

    Trả về None nếu không tìm thấy hoặc giá trị là chuỗi rỗng / placeholder.
    """
    val: Optional[str] = None

    # 1) Streamlit secrets
    try:
        import streamlit as st  # type: ignore
        try:
            if name in st.secrets:           # type: ignore[attr-defined]
                val = str(st.secrets[name])  # type: ignore[index]
        except Exception:
            pass
    except ImportError:
        pass

    # 2) Env / dotenv
    if not val:
        val = os.getenv(name)

    if not val:
        return None
    val = val.strip().strip('"').strip("'")
    if not val or val.lower() in {"none", "null", "your_key_here", "changeme"}:
        return None
    return val


# ── Khai báo provider được hỗ trợ ────────────────────────────────────────────
# Mỗi provider khai báo:
#   env_keys   : danh sách tên biến môi trường có thể chứa API key
#   models     : dict { model_id: nhãn hiển thị }
#   default    : model mặc định
#   lib_hint   : thư viện cần cài (để hiển thị thông báo khi thiếu)

PROVIDERS: dict[str, dict] = {
    "groq": {
        "label"   : "Groq",
        "env_keys": ["GROQ_API_KEY"],
        "lib_hint": "langchain-groq",
        "default" : "llama-3.3-70b-versatile",
        "models"  : {
            "llama-3.3-70b-versatile": "LLaMA 3.3 70B — Mạnh, tiếng Việt tốt",
            "llama-3.1-8b-instant"   : "LLaMA 3.1 8B — Nhanh, nhẹ",
            "gemma2-9b-it"           : "Gemma2 9B — Cân bằng",
            "mixtral-8x7b-32768"     : "Mixtral 8x7B — Context dài",
        },
    },
    "openai": {
        "label"   : "OpenAI",
        "env_keys": ["OPENAI_API_KEY"],
        "lib_hint": "langchain-openai",
        "default" : "gpt-4o-mini",
        "models"  : {
            "gpt-4o"      : "GPT-4o — Mạnh nhất",
            "gpt-4o-mini" : "GPT-4o mini — Nhanh, rẻ",
            "gpt-4-turbo" : "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo — Cũ, rẻ",
        },
    },
    "anthropic": {
        "label"   : "Anthropic (Claude)",
        "env_keys": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "lib_hint": "langchain-anthropic",
        "default" : "claude-3-5-sonnet-latest",
        "models"  : {
            "claude-3-5-sonnet-latest": "Claude 3.5 Sonnet — Mạnh",
            "claude-3-5-haiku-latest" : "Claude 3.5 Haiku — Nhanh",
            "claude-3-opus-latest"    : "Claude 3 Opus — Suy luận sâu",
        },
    },
    "google": {
        "label"   : "Google Gemini",
        "env_keys": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "lib_hint": "langchain-google-genai",
        "default" : "gemini-1.5-flash",
        "models"  : {
            "gemini-1.5-pro"  : "Gemini 1.5 Pro — Context cực dài",
            "gemini-1.5-flash": "Gemini 1.5 Flash — Nhanh, miễn phí",
            "gemini-2.0-flash-exp": "Gemini 2.0 Flash (experimental)",
        },
    },
    "deepseek": {
        "label"   : "DeepSeek",
        "env_keys": ["DEEPSEEK_API_KEY"],
        "lib_hint": "langchain-openai",      # dùng chung ChatOpenAI
        "base_url": "https://api.deepseek.com/v1",
        "default" : "deepseek-chat",
        "models"  : {
            "deepseek-chat"    : "DeepSeek-V3 — Mạnh, rẻ, tiếng Việt tốt",
            "deepseek-reasoner": "DeepSeek-R1 — Suy luận sâu (chậm hơn)",
        },
    },
}


# Provider mặc định nếu nhiều provider cùng có key (dev override bằng env)
DEFAULT_PROVIDER_ORDER = [
    os.getenv("CHATBOT_DEFAULT_PROVIDER", "").strip().lower(),
    "groq", "openai", "anthropic", "google", "deepseek",
]


# ── Nhãn nguồn tài liệu (filter retriever theo metadata.category) ────────────
# Mỗi nguồn tương ứng 1 thư mục con trong data/ (= metadata "category" của chunk).
SOURCE_CATEGORIES: dict[str, dict] = {
    "QD": {
        "label"      : "FPT (Quyết định nội bộ)",
        "short"      : "FPT",
        "icon"       : "🏢",
        "description": "Quyết định, hướng dẫn, KHGD của FSC/FPT",
    },
    "TT32_2018": {
        "label"      : "Bộ Giáo Dục (Thông tư 32/2018)",
        "short"      : "Bộ GD",
        "icon"       : "🏛️",
        "description": "CT GDPT 2018 — TT 32/2018/TT-BGDĐT và 27 môn học",
    },
}


def get_api_key(provider: str) -> Optional[str]:
    """Tìm API key của provider qua tất cả env keys khai báo."""
    info = PROVIDERS.get(provider)
    if not info:
        return None
    for env_key in info["env_keys"]:
        v = _get_secret(env_key)
        if v:
            return v
    return None


def available_providers() -> list[str]:
    """Danh sách provider có API key sẵn sàng (theo thứ tự ưu tiên)."""
    found = []
    for p in DEFAULT_PROVIDER_ORDER:
        if p and p in PROVIDERS and p not in found and get_api_key(p):
            found.append(p)
    # Bổ sung các provider còn lại cũng có key
    for p in PROVIDERS:
        if p not in found and get_api_key(p):
            found.append(p)
    return found


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Bạn là chuyên gia tư vấn về Phát triển Chương trình Giáo dục Phổ thông (PTCT PT) tại Việt Nam.
Nhiệm vụ: trả lời câu hỏi DỰA HOÀN TOÀN vào các tài liệu trong phần CONTEXT bên dưới.

Nguyên tắc bắt buộc:
1. KHÔNG tự suy diễn hay thêm thông tin ngoài Context.
2. Trình bày rõ ràng, dùng bullet point khi liệt kê.
3. SAU MỖI ý quan trọng phải đính kèm trích dẫn nguồn theo cú pháp Markdown: [Tên văn bản](URL)

--- CONTEXT ---
{context}
"""


SYSTEM_PROMPT_V2 = """\
Bạn là chuyên gia tư vấn về Phát triển Chương trình Giáo dục Phổ thông (PTCT PT) tại Việt Nam.
Bạn chỉ được sử dụng dữ liệu có trong CONTEXT.

Yêu cầu bắt buộc:
1. Trả lời ngắn gọn trước (2-5 ý), sau đó mới mở rộng nếu cần.
2. Mỗi ý quan trọng phải có trích dẫn nguồn dạng Markdown: [Tên văn bản](URL).
3. Khi nêu quy định cụ thể, trích nguyên văn trong dấu «...» từ CONTEXT.
4. Nếu có nhiều nguồn mâu thuẫn, liệt kê từng quan điểm theo nguồn.
5. Nếu CONTEXT chưa đủ chắc chắn, nêu rõ: "Context retrieved chưa đủ thông tin để khẳng định".
6. Không tự suy diễn ngoài CONTEXT.
"""


def get_embed_alias(alias: Optional[str]) -> str:
    """Chuẩn hóa alias embedding; fallback về mặc định nếu không hợp lệ."""
    if alias and alias in EMBED_MODELS:
        return alias
    return DEFAULT_EMBED_ALIAS


def get_embed_model_name(alias: Optional[str]) -> str:
    """Lấy model name từ alias embedding."""
    norm = get_embed_alias(alias)
    return EMBED_MODELS[norm]["name"]


def get_chunk_params(variant: Optional[str]) -> tuple[str, int, int]:
    """Trả về (variant, chunk_size, chunk_overlap)."""
    norm = variant if variant in CHUNK_VARIANTS else DEFAULT_CHUNK_VARIANT
    cfg = CHUNK_VARIANTS[norm]
    return norm, int(cfg["chunk_size"]), int(cfg["chunk_overlap"])


def get_chunking_strategy(strategy: Optional[str]) -> str:
    """Chuẩn hóa tên chiến lược chunking."""
    if strategy and strategy in CHUNKING_STRATEGIES:
        return strategy
    return DEFAULT_CHUNKING_STRATEGY


def build_collection_name(
    embed_alias: Optional[str],
    chunk_variant: Optional[str],
    chunking_strategy: Optional[str],
) -> str:
    """Định danh collection theo embedding + chunk variant + strategy."""
    emb = get_embed_alias(embed_alias)
    var, _, _ = get_chunk_params(chunk_variant)
    strategy = get_chunking_strategy(chunking_strategy)
    return f"{emb}__{var}__{strategy}"
