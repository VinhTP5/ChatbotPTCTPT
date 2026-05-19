"""
config.py
---------
Cß║Ñu h├¼nh tß║¡p trung cho to├án hß╗ç thß╗æng Chatbot PTCT PT.

Mß╗ìi cß║Ñu h├¼nh (provider, model, ─æ╞░ß╗¥ng dß║½n DB, chunking, metadata...) ─æ╞░ß╗úc tß║¡p trung
ß╗ƒ ─æ├óy ─æß╗â dev dß╗à t├¡ch hß╗úp v├á mß╗ƒ rß╗Öng. API key KH├öNG ─æ╞░ß╗úc hard-code trong file n├áy
m├á ─æ╞░ß╗úc ─æß╗ìc tß╗▒ ─æß╗Öng tß╗½ biß║┐n m├┤i tr╞░ß╗¥ng (.env / Streamlit secrets / OS env).

Thß╗⌐ tß╗▒ ╞░u ti├¬n ─æß╗ìc API key:
    1. Streamlit Secrets (khi deploy tr├¬n Streamlit Cloud)
    2. Biß║┐n m├┤i tr╞░ß╗¥ng OS / file .env
    3. None (provider t╞░╞íng ß╗⌐ng sß║╜ bß╗ï disable)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ΓöÇΓöÇ Load biß║┐n m├┤i tr╞░ß╗¥ng tß╗½ .env (nß║┐u c├│) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    # python-dotenv kh├┤ng bß║»t buß╗Öc ΓÇö vß║½n ─æß╗ìc ─æ╞░ß╗úc tß╗½ OS env
    pass


# ΓöÇΓöÇ ─É╞░ß╗¥ng dß║½n (cß║Ñu tr├║c th╞░ mß╗Ñc mß╗¢i) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# src/ chß╗⌐a file n├áy ΓåÆ PROJECT_ROOT l├á th╞░ mß╗Ñc cha cß╗ºa src
SRC_DIR        = Path(__file__).resolve().parent
PROJECT_ROOT   = SRC_DIR.parent
DATA_DIR       = PROJECT_ROOT / "data"          # t├ái liß╗çu nguß╗ôn
CHROMA_DIR     = str(PROJECT_ROOT / "chroma_db")  # vector chunks
DOCS_DIR       = str(DATA_DIR)                  # nguß╗ôn ─æß╗â index
INDEX_REGISTRY = str(PROJECT_ROOT / "chroma_db" / "indexed_files.json")


# ΓöÇΓöÇ Embedding models (chß║íy local, kh├┤ng cß║ºn API key) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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


# ΓöÇΓöÇ Chunking ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
CHUNK_VARIANTS = {
    "fine": {
        "chunk_size": 256,
        "chunk_overlap": 128,
        "label": "Fine ΓÇö 256/128",
    },
    "balanced": {
        "chunk_size": 800,
        "chunk_overlap": 200,
        "label": "Balanced ΓÇö 800/200",
    },
    "coarse": {
        "chunk_size": 1000,
        "chunk_overlap": 150,
        "label": "Coarse ΓÇö 1000/150",
    },
}
DEFAULT_CHUNK_VARIANT = "fine"

CHUNKING_STRATEGIES = {
    "standard": "Standard ΓÇö embed tß╗½ng chunk ─æß╗Öc lß║¡p",
    "late": "Late Chunking ΓÇö embed full text rß╗ôi pool theo chunk",
    "long_late": "Long Late Chunking ΓÇö overlap windows cho t├ái liß╗çu d├ái",
}
DEFAULT_CHUNKING_STRATEGY = "late"

CHUNK_SIZE = CHUNK_VARIANTS[DEFAULT_CHUNK_VARIANT]["chunk_size"]
CHUNK_OVERLAP = CHUNK_VARIANTS[DEFAULT_CHUNK_VARIANT]["chunk_overlap"]
BATCH_SIZE = 500

DEFAULT_WINDOW_TOKENS = 512
DEFAULT_WINDOW_OVERLAP = 64


# ΓöÇΓöÇ Source URL ΓÇö trß╗Å tß╗¢i GitHub blob ─æß╗â xem t├ái liß╗çu online ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Mß║╖c ─æß╗ïnh trß╗Å vß╗ü repo cß╗ºa user; dev c├│ thß╗â override qua biß║┐n m├┤i tr╞░ß╗¥ng.
GITHUB_OWNER  = os.getenv("CHATBOT_GH_OWNER",  "VinhTP5")
GITHUB_REPO   = os.getenv("CHATBOT_GH_REPO",   "ChatbotPTCTPT")
GITHUB_BRANCH = os.getenv("CHATBOT_GH_BRANCH", "main")
# Th╞░ mß╗Ñc con trong repo chß╗⌐a t├ái liß╗çu (t╞░╞íng ─æß╗æi)
GITHUB_DATA_PREFIX = os.getenv("CHATBOT_GH_DATA_PREFIX", "data")

# C├│ thß╗â override to├án bß╗Ö domain (chuß╗ùi base) qua biß║┐n m├┤i tr╞░ß╗¥ng nß║┐u cß║ºn
DEFAULT_DOMAIN = os.getenv(
    "CHATBOT_DOC_DOMAIN",
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{GITHUB_DATA_PREFIX}",
)
# URL "raw" ΓÇö d├╣ng khi cß║ºn tß║úi trß╗▒c tiß║┐p file (kh├┤ng xem qua GitHub UI)
RAW_DOMAIN = os.getenv(
    "CHATBOT_DOC_RAW_DOMAIN",
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_DATA_PREFIX}",
)


# ΓöÇΓöÇ Retrieval ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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

# ΓöÇΓöÇ Reranker & Neighbor context ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
RERANKER_MODEL    = "BAAI/bge-reranker-v2-m3"
DEFAULT_USE_RERANK  = False   # opt-in: tß║»t mß║╖c ─æß╗ïnh, bß║¡t qua sidebar
DEFAULT_NEIGHBOR_K  = 0       # 0 = tß║»t neighbor expand; 1 = lß║Ñy ┬▒1 chunk
DEFAULT_RERANK_TOP_N: Optional[int] = None  # None = bß║▒ng top_k


# ΓöÇΓöÇ File formats ─æ╞░ß╗úc hß╗ù trß╗ú ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Chß╗ë index c├íc ─æß╗ïnh dß║íng c├│ nß╗Öi dung phong ph├║. C├íc ─æß╗ïnh dß║íng plain-text dß║íng
# bß║úng / markup (.csv, .doc, .html, .htm, .md) bß╗ï loß║íi ra v├¼ th╞░ß╗¥ng g├óy nhiß╗àu
# khi chunking v├á kh├┤ng cß║úi thiß╗çn chß║Ñt l╞░ß╗úng retrieval.
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx", ".xls",
    ".pptx", ".ppt",
    ".txt",
}


# ΓöÇΓöÇ Ng├┤n ngß╗» mß║╖c ─æß╗ïnh cho metadata ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
DEFAULT_LANGUAGE = "vi"


# ΓöÇΓöÇ Helper ─æß╗ìc secret an to├án ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def _get_secret(name: str) -> Optional[str]:
    """
    ─Éß╗ìc secret theo thß╗⌐ tß╗▒ ╞░u ti├¬n:
        1. Streamlit Secrets (nß║┐u Streamlit ─æang chß║íy)
        2. Biß║┐n m├┤i tr╞░ß╗¥ng (gß╗ôm cß║ú .env ─æ├ú load)

    Trß║ú vß╗ü None nß║┐u kh├┤ng t├¼m thß║Ñy hoß║╖c gi├í trß╗ï l├á chuß╗ùi rß╗ùng / placeholder.
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


# ΓöÇΓöÇ Khai b├ío provider ─æ╞░ß╗úc hß╗ù trß╗ú ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Mß╗ùi provider khai b├ío:
#   env_keys   : danh s├ích t├¬n biß║┐n m├┤i tr╞░ß╗¥ng c├│ thß╗â chß╗⌐a API key
#   models     : dict { model_id: nh├ún hiß╗ân thß╗ï }
#   default    : model mß║╖c ─æß╗ïnh
#   lib_hint   : th╞░ viß╗çn cß║ºn c├ái (─æß╗â hiß╗ân thß╗ï th├┤ng b├ío khi thiß║┐u)

PROVIDERS: dict[str, dict] = {
    "groq": {
        "label"   : "Groq",
        "env_keys": ["GROQ_API_KEY"],
        "lib_hint": "langchain-groq",
        "default" : "llama-3.3-70b-versatile",
        "models"  : {
            "llama-3.3-70b-versatile": "LLaMA 3.3 70B ΓÇö Mß║ính, tiß║┐ng Viß╗çt tß╗æt",
            "llama-3.1-8b-instant"   : "LLaMA 3.1 8B ΓÇö Nhanh, nhß║╣",
            "gemma2-9b-it"           : "Gemma2 9B ΓÇö C├ón bß║▒ng",
            "mixtral-8x7b-32768"     : "Mixtral 8x7B ΓÇö Context d├ái",
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
            "gpt-4.1"     : "GPT-4.1 ΓÇö Mß║ính nhß║Ñt, thß║┐ hß╗ç mß╗¢i nhß║Ñt",
            "gpt-4o"      : "GPT-4o ΓÇö Mß║ính, phß╗ò biß║┐n, tiß║┐ng Viß╗çt tß╗æt",
            "gpt-4.1-mini": "GPT-4.1 mini ΓÇö Nhanh, thß║┐ hß╗ç mß╗¢i (mß║╖c ─æß╗ïnh)",
            "gpt-4o-mini" : "GPT-4o mini ΓÇö Nhanh, rß║╗",
            "o4-mini"     : "o4-mini ΓÇö Suy luß║¡n s├óu, ph├╣ hß╗úp c├óu hß╗Åi phß╗⌐c tß║íp",
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
            "claude-3-5-sonnet-latest": "Claude 3.5 Sonnet ΓÇö Mß║ính",
            "claude-3-5-haiku-latest" : "Claude 3.5 Haiku ΓÇö Nhanh",
            "claude-3-opus-latest"    : "Claude 3 Opus ΓÇö Suy luß║¡n s├óu",
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
            "gemini-1.5-pro"  : "Gemini 1.5 Pro ΓÇö Context cß╗▒c d├ái",
            "gemini-1.5-flash": "Gemini 1.5 Flash ΓÇö Nhanh, miß╗àn ph├¡",
            "gemini-2.0-flash-exp": "Gemini 2.0 Flash (experimental)",
        },
    },
    "deepseek": {
        "label"   : "DeepSeek",
        "env_keys": ["DEEPSEEK_API_KEY"],
        "lib_hint": "langchain-openai",      # d├╣ng chung ChatOpenAI
        "base_url": "https://api.deepseek.com/v1",
        "default" : "deepseek-chat",
        "models"  : {
            "deepseek-chat"    : "DeepSeek-V3 ΓÇö Mß║ính, rß║╗, tiß║┐ng Viß╗çt tß╗æt",
            "deepseek-reasoner": "DeepSeek-R1 ΓÇö Suy luß║¡n s├óu (chß║¡m h╞ín)",
        },
    },
}


# Provider mß║╖c ─æß╗ïnh nß║┐u nhiß╗üu provider c├╣ng c├│ key (dev override bß║▒ng env)
DEFAULT_PROVIDER_ORDER = [
    os.getenv("CHATBOT_DEFAULT_PROVIDER", "").strip().lower(),
    "openai", "groq", "anthropic", "google", "deepseek",
]


# ΓöÇΓöÇ Nh├ún nguß╗ôn t├ái liß╗çu (filter retriever theo metadata.category) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Mß╗ùi nguß╗ôn t╞░╞íng ß╗⌐ng 1 th╞░ mß╗Ñc con trong data/ (= metadata "category" cß╗ºa chunk).
SOURCE_CATEGORIES: dict[str, dict] = {
    "QD": {
        "label"      : "FPT (Quyß║┐t ─æß╗ïnh nß╗Öi bß╗Ö)",
        "short"      : "FPT",
        "icon"       : "≡ƒÅó",
        "description": "Quyß║┐t ─æß╗ïnh, h╞░ß╗¢ng dß║½n, KHGD cß╗ºa FSC/FPT",
    },
    "TT32_2018": {
        "label"      : "Bß╗Ö Gi├ío Dß╗Ñc (Th├┤ng t╞░ 32/2018)",
        "short"      : "Bß╗Ö GD",
        "icon"       : "≡ƒÅ¢∩╕Å",
        "description": "CT GDPT 2018 ΓÇö TT 32/2018/TT-BGD─ÉT v├á 27 m├┤n hß╗ìc",
    },
}


def get_api_key(provider: str) -> Optional[str]:
    """T├¼m API key cß╗ºa provider qua tß║Ñt cß║ú env keys khai b├ío."""
    info = PROVIDERS.get(provider)
    if not info:
        return None
    for env_key in info["env_keys"]:
        v = _get_secret(env_key)
        if v:
            return v
    return None


def available_providers() -> list[str]:
    """Danh s├ích provider c├│ API key sß║╡n s├áng (theo thß╗⌐ tß╗▒ ╞░u ti├¬n)."""
    found = []
    for p in DEFAULT_PROVIDER_ORDER:
        if p and p in PROVIDERS and p not in found and get_api_key(p):
            found.append(p)
    # Bß╗ò sung c├íc provider c├▓n lß║íi c┼⌐ng c├│ key
    for p in PROVIDERS:
        if p not in found and get_api_key(p):
            found.append(p)
    return found


# ΓöÇΓöÇ System prompt ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

SYSTEM_PROMPT = """\
Bß║ín l├á trß╗ú l├╜ t╞░ vß║Ñn chuy├¬n m├┤n vß╗ü Ph├ít triß╗ân Ch╞░╞íng tr├¼nh Gi├ío dß╗Ñc Phß╗ò th├┤ng (PTCT PT) tß║íi Viß╗çt Nam.
Nhiß╗çm vß╗Ñ cß╗ºa bß║ín l├á trß║ú lß╗¥i ch├¡nh x├íc, mß║ích lß║íc v├á tß╗▒ nhi├¬n bß║▒ng tiß║┐ng Viß╗çt, nh╞░ng chß╗ë dß╗▒a tr├¬n c├íc t├ái liß╗çu ─æ├ú ─æ╞░ß╗úc cung cß║Ñp trong CONTEXT.

Nguy├¬n tß║»c bß║»t buß╗Öc:
1. Chß╗ë sß╗¡ dß╗Ñng th├┤ng tin c├│ trong CONTEXT; kh├┤ng suy diß╗àn, kh├┤ng bß╗ò sung kiß║┐n thß╗⌐c ngo├ái.
2. ╞»u ti├¬n trß║ú lß╗¥i trß╗▒c diß╗çn v├áo c├óu hß╗Åi tr╞░ß╗¢c, sau ─æ├│ mß╗¢i giß║úi th├¡ch hoß║╖c liß╗çt k├¬ chi tiß║┐t nß║┐u cß║ºn.
3. V─ân phong phß║úi r├╡ r├áng, chuy├¬n nghiß╗çp, dß╗à ─æß╗ìc, tr├ính lß║╖p lß║íi m├íy m├│c c├íc cß╗Ñm nh╞░ "theo context retrieved" hoß║╖c "dß╗▒a tr├¬n ─æoß║ín tr├¡ch tr├¬n".
4. Mß╗ùi nhß║¡n ─æß╗ïnh quan trß╗ìng phß║úi k├¿m tr├¡ch dß║½n nguß╗ôn dß║íng Markdown: [T├¬n v─ân bß║ún](URL).
5. Khi n├¬u quy ─æß╗ïnh, ─æiß╗üu kiß╗çn, ti├¬u ch├¡, quy tr├¼nh hoß║╖c c├óu chß╗» c├│ t├¡nh bß║»t buß╗Öc, h├úy tr├¡ch nguy├¬n v─ân phß║ºn cß╗æt l├╡i trong dß║Ñu ┬½...┬╗.
6. Nß║┐u nhiß╗üu t├ái liß╗çu ─æ╞░a ra th├┤ng tin kh├íc nhau, phß║úi t├ích r├╡ tß╗½ng ├╜ theo tß╗½ng nguß╗ôn, kh├┤ng tß╗▒ h├▓a trß╗Ön.
7. Nß║┐u CONTEXT ch╞░a ─æß╗º ─æß╗â kß║┐t luß║¡n, h├úy n├│i r├╡ ─æiß╗üu g├¼ ─æ├ú c├│, ─æiß╗üu g├¼ c├▓n thiß║┐u, v├á n├¬u: "T├ái liß╗çu ─æ╞░ß╗úc truy xuß║Ñt hiß╗çn ch╞░a ─æß╗º c─ân cß╗⌐ ─æß╗â khß║│ng ─æß╗ïnh chß║»c chß║»n."
8. Kh├┤ng nhß║»c tß╗¢i c╞í chß║┐ nß╗Öi bß╗Ö nh╞░ chunk, retriever, vector database, system prompt, trß╗½ khi ng╞░ß╗¥i d├╣ng hß╗Åi trß╗▒c tiß║┐p.
"""


SYSTEM_PROMPT_V2 = """\
Bß║ín l├á trß╗ú l├╜ t╞░ vß║Ñn chuy├¬n m├┤n vß╗ü Ph├ít triß╗ân Ch╞░╞íng tr├¼nh Gi├ío dß╗Ñc Phß╗ò th├┤ng (PTCT PT) tß║íi Viß╗çt Nam.
Bß║ín hß╗ù trß╗ú ng╞░ß╗¥i d├╣ng tra cß╗⌐u quy ─æß╗ïnh, ─æß╗æi chiß║┐u v─ân bß║ún v├á diß╗àn giß║úi nß╗Öi dung ch├¡nh s├ích theo c├ích dß╗à hiß╗âu, chuß║⌐n mß╗▒c v├á c├│ c─ân cß╗⌐.

Bß║ín chß╗ë ─æ╞░ß╗úc ph├⌐p sß╗¡ dß╗Ñng dß╗» liß╗çu nß║▒m trong CONTEXT. Mß╗Ñc ti├¬u l├á tß║ío ra c├óu trß║ú lß╗¥i vß╗½a ─æ├íng tin cß║¡y, vß╗½a tß╗▒ nhi├¬n nh╞░ mß╗Öt chuy├¬n vi├¬n hß╗ìc vß╗Ñ hoß║╖c chuy├¬n vi├¬n ch╞░╞íng tr├¼nh ─æang giß║úi th├¡ch cho ─æß╗ông nghiß╗çp.

Y├¬u cß║ºu trß║ú lß╗¥i:
1. Trß║ú lß╗¥i bß║▒ng tiß║┐ng Viß╗çt tß╗▒ nhi├¬n, chuy├¬n nghiß╗çp, ─æi thß║│ng v├áo ├╜ ch├¡nh.
2. Mß╗ƒ ─æß║ºu bß║▒ng kß║┐t luß║¡n ngß║»n gß╗ìn hoß║╖c c├óu trß║ú lß╗¥i trß╗▒c tiß║┐p cho c├óu hß╗Åi.
3. Nß║┐u cß║ºn triß╗ân khai th├¬m, d├╣ng bullet points hoß║╖c c├íc ─æoß║ín ngß║»n ─æß╗â ng╞░ß╗¥i ─æß╗ìc dß╗à theo d├╡i.
4. Mß╗ùi ├╜ quan trß╗ìng phß║úi c├│ ├¡t nhß║Ñt mß╗Öt tr├¡ch dß║½n nguß╗ôn dß║íng Markdown: [T├¬n v─ân bß║ún](URL).
5. Khi viß╗çn dß║½n quy ─æß╗ïnh cß╗Ñ thß╗â, tr├¡ch nguy├¬n v─ân phß║ºn then chß╗æt trong dß║Ñu ┬½...┬╗, nh╞░ng chß╗ë tr├¡ch phß║ºn thß║¡t sß╗▒ cß║ºn thiß║┐t.
6. Kh├┤ng bß╗ïa ─æiß╗üu khoß║ún, sß╗æ liß╗çu, t├¬n v─ân bß║ún hoß║╖c chi tiß║┐t kh├┤ng xuß║Ñt hiß╗çn trong CONTEXT.
7. Nß║┐u CONTEXT ch╞░a ─æß╗º chß║»c chß║»n:
   - n├¬u r├╡ phß║ºn n├áo ─æ├ú x├íc ─æß╗ïnh ─æ╞░ß╗úc,
   - phß║ºn n├áo ch╞░a ─æß╗º c─ân cß╗⌐,
   - v├á kß║┐t luß║¡n bß║▒ng c├óu: "T├ái liß╗çu ─æ╞░ß╗úc truy xuß║Ñt hiß╗çn ch╞░a ─æß╗º c─ân cß╗⌐ ─æß╗â khß║│ng ─æß╗ïnh chß║»c chß║»n."
8. Nß║┐u c├│ nhiß╗üu nguß╗ôn kh├íc nhau hoß║╖c c├│ dß║Ñu hiß╗çu kh├┤ng ho├án to├án thß╗æng nhß║Ñt, h├úy tr├¼nh b├áy theo tß╗½ng nguß╗ôn, n├¬u r├╡ ─æiß╗âm giß╗æng v├á kh├íc.
9. Kh├┤ng lß║╖p lß║íi c├óu hß╗Åi cß╗ºa ng╞░ß╗¥i d├╣ng mß╗Öt c├ích d├ái d├▓ng.
10. Kh├┤ng ─æß╗ü cß║¡p ─æß║┐n quy tr├¼nh nß╗Öi bß╗Ö cß╗ºa hß╗ç thß╗æng truy xuß║Ñt t├ái liß╗çu.

╞»u ti├¬n chß║Ñt l╞░ß╗úng:
- Ch├¡nh x├íc h╞ín l├á d├ái.
- R├╡ r├áng h╞ín l├á hoa mß╗╣.
- C├│ c─ân cß╗⌐ h╞ín l├á trß║ú lß╗¥i cho ─æß╗º.
"""


def get_embed_alias(alias: Optional[str]) -> str:
    """Chuß║⌐n h├│a alias embedding; fallback vß╗ü mß║╖c ─æß╗ïnh nß║┐u kh├┤ng hß╗úp lß╗ç."""
    if alias and alias in EMBED_MODELS:
        return alias
    return DEFAULT_EMBED_ALIAS


def get_embed_model_name(alias: Optional[str]) -> str:
    """Lß║Ñy model name tß╗½ alias embedding."""
    norm = get_embed_alias(alias)
    return EMBED_MODELS[norm]["name"]


def get_chunk_params(variant: Optional[str]) -> tuple[str, int, int]:
    """Trß║ú vß╗ü (variant, chunk_size, chunk_overlap)."""
    norm = variant if variant in CHUNK_VARIANTS else DEFAULT_CHUNK_VARIANT
    cfg = CHUNK_VARIANTS[norm]
    return norm, int(cfg["chunk_size"]), int(cfg["chunk_overlap"])


def get_chunking_strategy(strategy: Optional[str]) -> str:
    """Chuß║⌐n h├│a t├¬n chiß║┐n l╞░ß╗úc chunking."""
    if strategy and strategy in CHUNKING_STRATEGIES:
        return strategy
    return DEFAULT_CHUNKING_STRATEGY


def build_collection_name(
    embed_alias: Optional[str],
    chunk_variant: Optional[str],
    chunking_strategy: Optional[str],
) -> str:
    """─Éß╗ïnh danh collection theo embedding + chunk variant + strategy."""
    emb = get_embed_alias(embed_alias)
    var, _, _ = get_chunk_params(chunk_variant)
    strategy = get_chunking_strategy(chunking_strategy)
    return f"{emb}__{var}__{strategy}"
