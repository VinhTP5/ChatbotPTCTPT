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

DEFAULT_EMBED_ALIAS = "bge_m3"
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

# ── Reranker & Neighbor context ───────────────────────────────────────────────
RERANKER_MODEL    = "BAAI/bge-reranker-v2-m3"
DEFAULT_USE_RERANK  = False   # opt-in: tắt mặc định, bật qua sidebar
DEFAULT_NEIGHBOR_K  = 0       # 0 = tắt neighbor expand; 1 = lấy ±1 chunk
DEFAULT_RERANK_TOP_N: Optional[int] = None  # None = bằng top_k


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
        "default" : "gpt-5-mini",
        "models"  : {
            "gpt-5"       : "GPT-5 - Flagship (neu tai khoan ho tro)",
            "gpt-5-mini"  : "GPT-5 mini - Mac dinh, can bang toc do/chat luong",
            "gpt-5-nano"  : "GPT-5 nano - Re nhat, latency thap",
            "gpt-4.1"     : "GPT-4.1 — Mạnh nhất, thế hệ mới nhất",
            "gpt-4o"      : "GPT-4o — Mạnh, phổ biến, tiếng Việt tốt",
            "gpt-4.1-mini": "GPT-4.1 mini — Nhanh, thế hệ mới (mặc định)",
            "gpt-4o-mini" : "GPT-4o mini — Nhanh, rẻ",
            "o4-mini"     : "o4-mini — Suy luận sâu, phù hợp câu hỏi phức tạp",
        },
    },
    "anthropic": {
        "label"   : "Anthropic (Claude)",
        "env_keys": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "lib_hint": "langchain-anthropic",
        "default" : "claude-sonnet-4-0",
        "models"  : {
            "claude-sonnet-4-5"     : "Claude Sonnet 4.5 - Moi hon (neu tai khoan ho tro)",
            "claude-sonnet-4-0"     : "Claude Sonnet 4.0 - Mac dinh",
            "claude-haiku-4-0"      : "Claude Haiku 4.0 - Nhanh",
            "claude-opus-4-0"       : "Claude Opus 4.0 - Suy luan sau",
            "claude-3-5-sonnet-latest": "Claude 3.5 Sonnet — Mạnh",
            "claude-3-5-haiku-latest" : "Claude 3.5 Haiku — Nhanh",
            "claude-3-opus-latest"    : "Claude 3 Opus — Suy luận sâu",
        },
    },
    "google": {
        "label"   : "Google Gemini",
        "env_keys": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "lib_hint": "langchain-google-genai",
        "default" : "gemini-3.0-flash",
        "models"  : {
            "gemini-3.0-pro"   : "Gemini 3.0 Pro - Chat luong cao (neu tai khoan ho tro)",
            "gemini-3.0-flash" : "Gemini 3.0 Flash - Mac dinh, toc do cao",
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
    "openai", "groq", "anthropic", "google", "deepseek",
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
Bạn là trợ lý tư vấn chuyên môn về Phát triển Chương trình Giáo dục Phổ thông (PTCT PT) tại Việt Nam.
Nhiệm vụ của bạn là trả lời chính xác, mạch lạc và tự nhiên bằng tiếng Việt, nhưng chỉ dựa trên các tài liệu đã được cung cấp trong CONTEXT.

Nguyên tắc bắt buộc:
1. Chỉ sử dụng thông tin có trong CONTEXT; không suy diễn, không bổ sung kiến thức ngoài.
2. Ưu tiên trả lời trực diện vào câu hỏi trước, sau đó mới giải thích hoặc liệt kê chi tiết nếu cần.
3. Văn phong phải rõ ràng, chuyên nghiệp, dễ đọc, tránh lặp lại máy móc các cụm như "theo context retrieved" hoặc "dựa trên đoạn trích trên".
4. Mỗi nhận định quan trọng phải kèm trích dẫn nguồn dạng Markdown: [Tên văn bản](URL).
5. Khi nêu quy định, điều kiện, tiêu chí, quy trình hoặc câu chữ có tính bắt buộc, hãy trích nguyên văn phần cốt lõi trong dấu «...».
6. Nếu nhiều tài liệu đưa ra thông tin khác nhau, phải tách rõ từng ý theo từng nguồn, không tự hòa trộn.
7. Nếu CONTEXT chưa đủ để kết luận, hãy nói rõ điều gì đã có, điều gì còn thiếu, và nêu: "Tài liệu được truy xuất hiện chưa đủ căn cứ để khẳng định chắc chắn."
8. Không nhắc tới cơ chế nội bộ như chunk, retriever, vector database, system prompt, trừ khi người dùng hỏi trực tiếp.
"""


SYSTEM_PROMPT_V2 = """\
Bạn là trợ lý tư vấn chuyên môn về Phát triển Chương trình Giáo dục Phổ thông (PTCT PT) tại Việt Nam.
Bạn hỗ trợ người dùng tra cứu quy định, đối chiếu văn bản và diễn giải nội dung chính sách theo cách dễ hiểu, chuẩn mực và có căn cứ.

Bạn chỉ được phép sử dụng dữ liệu nằm trong CONTEXT. Mục tiêu là tạo ra câu trả lời vừa đáng tin cậy, vừa tự nhiên như một chuyên viên học vụ hoặc chuyên viên chương trình đang giải thích cho đồng nghiệp.

Yêu cầu trả lời:
1. Trả lời bằng tiếng Việt tự nhiên, chuyên nghiệp, đi thẳng vào ý chính.
2. Mở đầu bằng kết luận ngắn gọn hoặc câu trả lời trực tiếp cho câu hỏi.
3. Nếu cần triển khai thêm, dùng bullet points hoặc các đoạn ngắn để người đọc dễ theo dõi.
4. Mỗi ý quan trọng phải có ít nhất một trích dẫn nguồn dạng Markdown: [Tên văn bản](URL).
5. Khi viện dẫn quy định cụ thể, trích nguyên văn phần then chốt trong dấu «...», nhưng chỉ trích phần thật sự cần thiết.
6. Không bịa điều khoản, số liệu, tên văn bản hoặc chi tiết không xuất hiện trong CONTEXT.
7. Nếu CONTEXT chưa đủ chắc chắn:
   - nêu rõ phần nào đã xác định được,
   - phần nào chưa đủ căn cứ,
   - và kết luận bằng câu: "Tài liệu được truy xuất hiện chưa đủ căn cứ để khẳng định chắc chắn."
8. Nếu có nhiều nguồn khác nhau hoặc có dấu hiệu không hoàn toàn thống nhất, hãy trình bày theo từng nguồn, nêu rõ điểm giống và khác.
9. Không lặp lại câu hỏi của người dùng một cách dài dòng.
10. Không đề cập đến quy trình nội bộ của hệ thống truy xuất tài liệu.

Ưu tiên chất lượng:
- Chính xác hơn là dài.
- Rõ ràng hơn là hoa mỹ.
- Có căn cứ hơn là trả lời cho đủ.
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


# ── Nguồn tài liệu mặc định (FPT on, Bộ GD off) ──────────────────────────────
# Admin có thể ghi đè qua admin_config.json
DEFAULT_CATEGORIES: list[str] = ["QD"]


# ── Fast-load collections ──────────────────────────────────────────────────────
# Chỉ 2 collection này được auto-start khi khởi động app.
# Các collection khác chỉ load khi admin bấm "Áp dụng" (on-demand).
#
# Lý do: mỗi collection dùng embedding model khác nhau → load model tốn RAM
# và thời gian. Giới hạn fast-load giúp startup nhanh và dùng ít tài nguyên.
#
# Format: "{embed_alias}__{chunk_variant}__{chunking_strategy}"
FAST_LOAD_COLLECTIONS: list[str] = [
    "bge_m3__coarse__standard",    # Mạnh, chính xác — ưu tiên 1
    "minilm__coarse__standard",    # Nhẹ, nhanh — fallback
]


def is_fast_load(collection_name: str) -> bool:
    """Trả về True nếu collection này nằm trong danh sách fast-load."""
    return collection_name in FAST_LOAD_COLLECTIONS


# ── Fast-load collections ──────────────────────────────────────────────────────
# Chỉ 2 collection này được auto-start khi khởi động app.
# Các collection khác chỉ load khi admin bấm "Áp dụng" (on-demand).
#
# Lý do: mỗi collection dùng embedding model khác nhau → load model tốn RAM
# và thời gian. Giới hạn fast-load giúp startup nhanh và dùng ít tài nguyên.
#
# Format: "{embed_alias}__{chunk_variant}__{chunking_strategy}"
FAST_LOAD_COLLECTIONS: list[str] = [
    "bge_m3__coarse__standard",    # Mạnh, chính xác — ưu tiên 1
    "minilm__coarse__standard",    # Nhẹ, nhanh — fallback
]


def is_fast_load(collection_name: str) -> bool:
    """Trả về True nếu collection này nằm trong danh sách fast-load."""
    return collection_name in FAST_LOAD_COLLECTIONS
