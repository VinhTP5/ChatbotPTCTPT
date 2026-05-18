"""
llm_providers.py
----------------
Lớp trừu tượng cho nhiều nhà cung cấp LLM:
    - Groq        (langchain-groq)
    - OpenAI      (langchain-openai)
    - Anthropic   (langchain-anthropic)
    - Google      (langchain-google-genai)

Dev tích hợp bằng cách đặt API key tương ứng vào biến môi trường hoặc
Streamlit Secrets. Người dùng cuối KHÔNG cần nhập key.

Sử dụng:
    from llm_providers import build_llm, list_available_models

    llm = build_llm()                  # auto chọn provider có key
    llm = build_llm("openai", "gpt-4o")
    models = list_available_models()   # đầy đủ provider/model đã sẵn sàng
"""

from __future__ import annotations

from typing import Any, Optional

from config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    PROVIDERS,
    available_providers,
    get_api_key,
)


class ProviderUnavailableError(RuntimeError):
    """Provider chưa được cấu hình hoặc thư viện chưa cài."""


class NoProviderConfiguredError(RuntimeError):
    """Không tìm thấy bất kỳ API key nào trong env/secrets."""


# ── Factory cho từng provider ────────────────────────────────────────────────

def _build_groq(model: str, api_key: str, temperature: float, max_tokens: int):
    try:
        from langchain_groq import ChatGroq
    except ImportError as e:
        raise ProviderUnavailableError(
            "Thiếu package 'langchain-groq'. Cài: pip install langchain-groq"
        ) from e
    return ChatGroq(
        model       = model,
        api_key     = api_key,
        temperature = temperature,
        max_tokens  = max_tokens,
    )


def _build_openai(model: str, api_key: str, temperature: float, max_tokens: int):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ProviderUnavailableError(
            "Thiếu package 'langchain-openai'. Cài: pip install langchain-openai"
        ) from e
    return ChatOpenAI(
        model       = model,
        api_key     = api_key,
        temperature = temperature,
        max_tokens  = max_tokens,
    )


def _build_anthropic(model: str, api_key: str, temperature: float, max_tokens: int):
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        raise ProviderUnavailableError(
            "Thiếu package 'langchain-anthropic'. Cài: pip install langchain-anthropic"
        ) from e
    return ChatAnthropic(
        model       = model,
        api_key     = api_key,
        temperature = temperature,
        max_tokens  = max_tokens,
    )


def _build_google(model: str, api_key: str, temperature: float, max_tokens: int):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as e:
        raise ProviderUnavailableError(
            "Thiếu package 'langchain-google-genai'. Cài: pip install langchain-google-genai"
        ) from e
    return ChatGoogleGenerativeAI(
        model                  = model,
        google_api_key         = api_key,
        temperature            = temperature,
        max_output_tokens      = max_tokens,
    )


def _build_openai_compatible(
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    base_url: str,
):
    """Builder dùng chung cho mọi provider tương thích OpenAI API.

    Dùng cho: DeepSeek, xAI Grok, OpenRouter, Together AI, Mistral (via OpenAI),
    Ollama / vLLM / LM Studio (self-host), …
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ProviderUnavailableError(
            "Thiếu package 'langchain-openai'. Cài: pip install langchain-openai"
        ) from e
    return ChatOpenAI(
        model       = model,
        api_key     = api_key,
        base_url    = base_url,
        temperature = temperature,
        max_tokens  = max_tokens,
    )


def _build_deepseek(model: str, api_key: str, temperature: float, max_tokens: int):
    return _build_openai_compatible(
        model, api_key, temperature, max_tokens,
        base_url=PROVIDERS["deepseek"]["base_url"],
    )


_BUILDERS = {
    "groq"     : _build_groq,
    "openai"   : _build_openai,
    "anthropic": _build_anthropic,
    "google"   : _build_google,
    "deepseek" : _build_deepseek,
}


# ── API công khai ─────────────────────────────────────────────────────────────

def resolve_provider(provider: Optional[str] = None) -> str:
    """Chọn provider phù hợp: ưu tiên tham số, sau đó tới provider có key."""
    if provider:
        provider = provider.strip().lower()
        if provider not in PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' không được hỗ trợ. "
                f"Hỗ trợ: {', '.join(PROVIDERS.keys())}"
            )
        if not get_api_key(provider):
            raise ProviderUnavailableError(
                f"Provider '{provider}' chưa có API key. "
                f"Thiết lập biến môi trường {PROVIDERS[provider]['env_keys'][0]}."
            )
        return provider

    avail = available_providers()
    if not avail:
        raise NoProviderConfiguredError(
            "Chưa có API key cho bất kỳ provider nào.\n"
            "Hãy thiết lập một trong các biến môi trường: "
            + ", ".join(
                info["env_keys"][0] for info in PROVIDERS.values()
            )
        )
    return avail[0]


def resolve_model(provider: str, model: Optional[str] = None) -> str:
    """Chọn model: ưu tiên tham số nếu hợp lệ, không thì lấy mặc định."""
    info = PROVIDERS[provider]
    if model and model in info["models"]:
        return model
    if model:
        # cho phép model lạ (custom), nhưng cảnh báo bằng cách trả về như cũ
        return model
    return info["default"]


def build_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Any:
    """Khởi tạo LLM phù hợp. Tự chọn provider nếu không truyền."""
    provider = resolve_provider(provider)
    model    = resolve_model(provider, model)
    api_key  = get_api_key(provider)

    builder = _BUILDERS[provider]
    return builder(model, api_key, temperature, max_tokens)


def list_available_models() -> dict[str, dict[str, str]]:
    """Trả về danh sách provider/model đã sẵn sàng (có API key)."""
    result: dict[str, dict[str, str]] = {}
    for p in available_providers():
        result[p] = dict(PROVIDERS[p]["models"])
    return result


def describe_status() -> str:
    """Trả về chuỗi mô tả trạng thái cấu hình LLM (dùng để hiển thị/log)."""
    avail = available_providers()
    if not avail:
        return (
            "❌ Chưa cấu hình API key cho bất kỳ provider nào.\n"
            "   Dev cần thiết lập 1 trong các biến: "
            + ", ".join(info["env_keys"][0] for info in PROVIDERS.values())
        )
    lines = ["✅ Provider sẵn sàng:"]
    for p in avail:
        lines.append(f"   • {PROVIDERS[p]['label']} ({len(PROVIDERS[p]['models'])} models)")
    return "\n".join(lines)
