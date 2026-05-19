"""
rag_engine.py
-------------
Module lõi RAG: load vectorstore, khởi tạo LLM (đa nhà cung cấp), build chain.

Khác với phiên bản cũ:
    - KHÔNG yêu cầu người dùng nhập API key (dev tích hợp qua env/secrets).
    - Hỗ trợ nhiều provider: Groq, OpenAI, Anthropic Claude, Google Gemini.
    - Tối ưu chain: retrieve 1 lần duy nhất cho mỗi câu hỏi.
"""

from __future__ import annotations

import logging
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings

from config import (
    CHROMA_DIR,
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
    PROVIDERS,
    RERANKER_MODEL,
    SYSTEM_PROMPT_V2,
    build_collection_name,
    get_chunking_strategy,
    get_chunk_params,
    get_embed_alias,
    get_embed_model_name,
)
from llm_providers import (
    NoProviderConfiguredError,
    ProviderUnavailableError,
    build_llm,
    is_model_access_error,
    list_fallback_models,
    resolve_model,
    resolve_provider,
)

# Export lại để app.py có thể dùng (giữ tương thích ngược)
__all__ = [
    "CHROMA_DIR",
    "DEFAULT_EMBED_ALIAS",
    "PROVIDERS",
    "NoProviderConfiguredError",
    "ProviderUnavailableError",
    "RAGResult",
    "format_docs",
    "get_unique_sources",
    "list_available_collections",
    "load_rag_engine",
    "resolve_model",
    "resolve_provider",
]

logger = logging.getLogger(__name__)


# ── Helper functions ──────────────────────────────────────────────────────────

def _normalize_chroma_dir(chroma_dir: str) -> str:
    """Chuẩn hóa đường dẫn Chroma để cache key ổn định giữa các lần gọi."""
    return str(Path(chroma_dir).resolve())


def _db_signature(chroma_dir: str) -> tuple[tuple[str, int, int], ...]:
    """
    Tạo chữ ký nhẹ của thư mục ChromaDB để cache tự invalid khi DB thay đổi.

    Dùng tên file + kích thước + mtime_ns cho các file top-level trong chroma_db/.
    """
    db_path = Path(chroma_dir)
    if not db_path.exists():
        return ()

    entries: list[tuple[str, int, int]] = []
    for child in sorted(db_path.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file():
            continue
        stat = child.stat()
        entries.append((child.name, int(stat.st_size), int(stat.st_mtime_ns)))
    return tuple(entries)


@lru_cache(maxsize=8)
def _get_embeddings(embed_alias: str) -> HuggingFaceEmbeddings:
    """Cache embedding model theo alias để tránh load lại giữa các rerun/session."""
    model_name = get_embed_model_name(embed_alias)
    logger.info("[RAGEngine] Loading embeddings %s -> %s", embed_alias, model_name)
    return HuggingFaceEmbeddings(
        model_name=model_name,
        show_progress=False,
        encode_kwargs={"batch_size": 64},
    )


@lru_cache(maxsize=32)
def _get_vectorstore(
    chroma_dir: str,
    collection_name: str,
    embed_alias: str,
    db_signature: tuple[tuple[str, int, int], ...],
) -> Chroma:
    """Cache Chroma vectorstore theo collection và chữ ký DB."""
    del db_signature
    return Chroma(
        persist_directory=chroma_dir,
        embedding_function=_get_embeddings(embed_alias),
        collection_name=collection_name,
    )


@lru_cache(maxsize=32)
def _get_collection_count(
    chroma_dir: str,
    collection_name: str,
    embed_alias: str,
    db_signature: tuple[tuple[str, int, int], ...],
) -> int:
    """Cache doc_count của collection tương ứng với trạng thái DB hiện tại."""
    return _get_vectorstore(
        chroma_dir=chroma_dir,
        collection_name=collection_name,
        embed_alias=embed_alias,
        db_signature=db_signature,
    )._collection.count()


@lru_cache(maxsize=8)
def _list_available_collections_cached(
    chroma_dir: str,
    db_signature: tuple[tuple[str, int, int], ...],
) -> tuple[str, ...]:
    """Cache danh sách collection để sidebar không query PersistentClient lặp lại."""
    del db_signature
    client = chromadb.PersistentClient(path=chroma_dir)
    return tuple(sorted(c.name for c in client.list_collections()))

def format_docs(docs: list[Document]) -> str:
    """Ghép docs thành context có cấu trúc rõ ràng để LLM bám nguồn tốt hơn."""
    parts: list[str] = []
    for index, doc in enumerate(docs, start=1):
        meta = doc.metadata or {}
        name = meta.get("document_name") or meta.get("file_name") or "Không rõ"
        url  = meta.get("source_url", "")
        page = meta.get("page_number")
        category = meta.get("category") or "Không rõ"
        chunk_index = meta.get("chunk_index")
        lines = [f"[Tài liệu {index}]"]
        lines.append(f"Tên văn bản: {name}")
        lines.append(f"Nhóm tài liệu: {category}")
        if page:
            lines.append(f"Trang: {page}")
        if chunk_index is not None:
            lines.append(f"Chunk: {chunk_index}")
        if url:
            lines.append(f"URL nguồn: {url}")
        lines.append("Nội dung trích:")
        lines.append(doc.page_content)
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def get_unique_sources(docs: list[Document]) -> list[dict]:
    """Trích xuất danh sách nguồn duy nhất từ docs."""
    seen: set[str] = set()
    sources: list[dict] = []
    for doc in docs:
        meta  = doc.metadata or {}
        url   = meta.get("source_url", "") or ""
        name  = meta.get("document_name") or meta.get("file_name") or "Không rõ"
        ftype = meta.get("file_type", "") or ""
        key   = url or f"{name}|{ftype}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "name"        : name,
            "url"         : url,                       # GitHub blob (xem online)
            "raw_url"     : meta.get("raw_url", ""),   # raw — tải file
            "path"        : meta.get("file_path", ""),
            "type"        : ftype,
            "page"        : meta.get("page_number"),
            "category"    : meta.get("category"),
            "file_size_kb": meta.get("file_size_kb"),
        })
    return sources


# ── Kết quả chuẩn hoá ─────────────────────────────────────────────────────────

class RAGResult:
    """Kết quả của 1 lần hỏi: câu trả lời + sources + docs gốc."""

    __slots__ = ("answer", "sources", "docs", "docs_with_scores")

    def __init__(
        self,
        answer: str,
        sources: list[dict],
        docs: list[Document],
        docs_with_scores: Optional[list[dict]] = None,
    ):
        self.answer  = answer
        self.sources = sources
        self.docs    = docs
        self.docs_with_scores = docs_with_scores or []

    def __repr__(self) -> str:  # pragma: no cover
        return f"RAGResult(answer={self.answer[:60]!r}..., n_sources={len(self.sources)})"


# ── Main engine ───────────────────────────────────────────────────────────────

class RAGEngine:
    """Đóng gói retriever + LLM + chain. Hỏi 1 câu chỉ retrieve 1 lần."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
        search_type: str = DEFAULT_SEARCH_TYPE,
        fetch_k: int = DEFAULT_FETCH_K,
        lambda_mult: float = DEFAULT_LAMBDA_MULT,
        score_threshold: Optional[float] = DEFAULT_SCORE_THRESHOLD,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        chroma_dir: str = CHROMA_DIR,
        embed_alias: str = DEFAULT_EMBED_ALIAS,
        chunk_variant: str = DEFAULT_CHUNK_VARIANT,
        chunking_strategy: str = DEFAULT_CHUNKING_STRATEGY,
        categories: Optional[list[str]] = None,
        use_rerank: bool = DEFAULT_USE_RERANK,
        neighbor_k: int = DEFAULT_NEIGHBOR_K,
        rerank_top_n: Optional[int] = DEFAULT_RERANK_TOP_N,
    ):
        # 1) Kiểm tra DB
        chroma_dir = _normalize_chroma_dir(chroma_dir)
        db_path = Path(chroma_dir)
        if not db_path.exists() or not any(db_path.iterdir()):
            raise FileNotFoundError(
                f"Không tìm thấy Vector Database tại '{chroma_dir}'.\n"
                "Hãy chạy: python build_db.py --mode rebuild"
            )
        db_signature = _db_signature(chroma_dir)

        # 2) Embeddings + vectorstore
        self.embed_alias = get_embed_alias(embed_alias)
        self.chunk_variant, self.chunk_size, self.chunk_overlap = get_chunk_params(chunk_variant)
        self.chunking_strategy = get_chunking_strategy(chunking_strategy)
        self.collection_name = build_collection_name(
            self.embed_alias,
            self.chunk_variant,
            self.chunking_strategy,
        )

        self.embeddings = _get_embeddings(self.embed_alias)
        self.vectorstore = _get_vectorstore(
            chroma_dir=chroma_dir,
            collection_name=self.collection_name,
            embed_alias=self.embed_alias,
            db_signature=db_signature,
        )
        self.doc_count = _get_collection_count(
            chroma_dir=chroma_dir,
            collection_name=self.collection_name,
            embed_alias=self.embed_alias,
            db_signature=db_signature,
        )
        if self.doc_count == 0:
            raise ValueError("Vector Database rỗng. Hãy chạy build_db.py để index tài liệu.")

        # Lưu retrieval params và categories — tạo retriever qua method dùng chung
        self._top_k = top_k
        self._search_type = search_type
        self._fetch_k = fetch_k
        self._lambda_mult = lambda_mult
        self._score_threshold = score_threshold
        self._categories: Optional[list[str]] = None
        self.retriever = None  # type: ignore[assignment]
        self.set_retrieval_params(
            top_k=top_k,
            search_type=search_type,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            score_threshold=score_threshold,
            categories=categories,
        )

        # Neighbor context & Reranker (opt-in)
        self._neighbor_k: int = max(0, int(neighbor_k))
        self._use_rerank: bool = bool(use_rerank)
        self._rerank_top_n: Optional[int] = rerank_top_n
        self._reranker = None  # lazy load khi cần
        if self._use_rerank:
            self._load_reranker()

        # 3) Provider & LLM
        self.provider = resolve_provider(provider)
        self.model    = resolve_model(self.provider, model)
        self._temperature = temperature
        self._max_tokens = max_tokens
        self.llm = build_llm(
            provider    = self.provider,
            model       = self.model,
            temperature = temperature,
            max_tokens  = max_tokens,
        )

        # 4) Prompt + chain (lazy compose để dùng context đã retrieve sẵn)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_V2),
            (
                "human",
                "Câu hỏi của người dùng:\n{input}\n\n"
                "CONTEXT TRÍCH XUẤT TỪ KHO TÀI LIỆU:\n"
                "{context}\n\n"
                "Hãy tạo câu trả lời cuối cùng bằng tiếng Việt, bám sát tài liệu và có trích dẫn nguồn.",
            ),
        ])
        self._answer_chain = self.prompt | self.llm | StrOutputParser()

    def _rebuild_llm_with_model(self, model_name: str) -> None:
        """Rebuild LLM + chain với model mới trên cùng provider."""
        self.llm = build_llm(
            provider=self.provider,
            model=model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        self.model = model_name
        self._answer_chain = self.prompt | self.llm | StrOutputParser()

    def _fallback_and_retry_answer(self, question: str, context: str, first_error: Exception) -> str:
        """Tự động fallback model khi model hiện tại không có quyền truy cập."""
        if not is_model_access_error(first_error):
            raise first_error

        attempted = [self.model]
        for candidate in list_fallback_models(self.provider, self.model):
            try:
                logger.warning(
                    "[RAGEngine] Model '%s' khong truy cap duoc, fallback sang '%s'",
                    attempted[-1],
                    candidate,
                )
                self._rebuild_llm_with_model(candidate)
                return self._answer_chain.invoke({"input": question, "context": context})
            except Exception as err:
                attempted.append(candidate)
                if not is_model_access_error(err):
                    raise err

        attempted_str = ", ".join(attempted)
        raise ProviderUnavailableError(
            f"Khong model nao truy cap duoc voi provider '{self.provider}'. Da thu: {attempted_str}."
        ) from first_error

    # ── Reranker & Neighbor helpers ──────────────────────────────────────────

    def _load_reranker(self) -> None:
        """Lazy load BGEReranker (tái dùng singleton)."""
        try:
            from reranker import get_reranker
            self._reranker = get_reranker(RERANKER_MODEL)
        except Exception as exc:
            logger.warning("[RAGEngine] Không thể load reranker: %s", exc)
            self._use_rerank = False
            self._reranker = None

    def _expand_with_neighbors(self, docs: list[Document]) -> list[Document]:
        """
        Mở rộng context bằng cách lấy thêm chunk liền kề (±neighbor_k) trong
        cùng tài liệu.

        Quy trình:
          1. Với mỗi doc, lấy document_name và chunk_index từ metadata.
          2. Query Chroma với where filter theo document_name, lọc chunk_index
             trong [idx - neighbor_k, idx + neighbor_k].
          3. Deduplicate theo chunk_index rồi merge vào danh sách gốc.
        """
        if self._neighbor_k <= 0 or not docs:
            return docs

        seen_keys: set[str] = set()
        expanded: list[Document] = []

        # Thêm docs gốc vào tập seen trước
        for doc in docs:
            meta = doc.metadata or {}
            key = f"{meta.get('document_name', '')}|{meta.get('chunk_index', '')}"
            seen_keys.add(key)
            expanded.append(doc)

        # Với mỗi doc gốc, lấy các chunk láng giềng
        for doc in docs:
            meta = doc.metadata or {}
            doc_name = meta.get("document_name")
            chunk_idx = meta.get("chunk_index")

            if not doc_name or chunk_idx is None:
                continue

            try:
                chunk_idx = int(chunk_idx)
            except (ValueError, TypeError):
                continue

            lo = chunk_idx - self._neighbor_k
            hi = chunk_idx + self._neighbor_k

            try:
                # Lấy toàn bộ chunk của document này (giới hạn để tránh quá nhiều)
                results = self.vectorstore.get(
                    where={"document_name": doc_name},
                    limit=200,
                    include=["documents", "metadatas"],
                )
                neighbor_docs = results.get("documents", [])
                neighbor_metas = results.get("metadatas", [])

                for content, nmeta in zip(neighbor_docs, neighbor_metas):
                    cidx = nmeta.get("chunk_index")
                    if cidx is None:
                        continue
                    try:
                        cidx = int(cidx)
                    except (ValueError, TypeError):
                        continue

                    if not (lo <= cidx <= hi):
                        continue

                    n_key = f"{doc_name}|{cidx}"
                    if n_key in seen_keys:
                        continue
                    seen_keys.add(n_key)
                    expanded.append(Document(page_content=content, metadata=nmeta))

            except Exception as exc:
                logger.debug("[RAGEngine] neighbor expand error for %s: %s", doc_name, exc)

        return expanded

    # ── Quản lý filter nguồn ─────────────────────────────────────────────────

    @staticmethod
    def _build_filter(categories: Optional[list[str]]) -> Optional[dict]:
        """Tạo metadata filter cho ChromaDB từ danh sách categories."""
        if not categories:
            return None
        cats = [c for c in categories if c]
        if not cats:
            return None
        if len(cats) == 1:
            return {"category": cats[0]}
        return {"category": {"$in": cats}}

    def _build_search_kwargs(self) -> dict:
        """Tạo search kwargs dựa trên retrieval mode hiện tại."""
        kwargs: dict[str, Any] = {"k": self._top_k}

        if self._search_type == "mmr":
            kwargs["fetch_k"] = max(self._fetch_k, self._top_k)
            kwargs["lambda_mult"] = float(self._lambda_mult)
        elif self._search_type == "similarity_score_threshold":
            threshold = (
                float(self._score_threshold)
                if self._score_threshold is not None
                else 0.3
            )
            kwargs["score_threshold"] = threshold

        flt = self._build_filter(self._categories)
        if flt is not None:
            kwargs["filter"] = flt
        return kwargs

    def _rebuild_retriever(self) -> None:
        self.retriever = self.vectorstore.as_retriever(
            search_type=self._search_type,
            search_kwargs=self._build_search_kwargs(),
        )

    def set_categories(self, categories: Optional[list[str]]) -> None:
        """Cập nhật bộ lọc nguồn (giảm số chunk cần duyệt)."""
        self._categories = list(categories) if categories else None
        self._rebuild_retriever()

    def set_retrieval_params(
        self,
        top_k: Optional[int] = None,
        search_type: Optional[str] = None,
        fetch_k: Optional[int] = None,
        lambda_mult: Optional[float] = None,
        score_threshold: Optional[float] = None,
        categories: Optional[list[str]] = None,
        use_rerank: Optional[bool] = None,
        neighbor_k: Optional[int] = None,
        rerank_top_n: Optional[int] = None,
    ) -> None:
        """Cập nhật retrieval params runtime mà không cần reload model."""
        if top_k is not None:
            self._top_k = int(top_k)
        if search_type is not None:
            self._search_type = search_type
        if fetch_k is not None:
            self._fetch_k = int(fetch_k)
        if lambda_mult is not None:
            self._lambda_mult = float(lambda_mult)
        if score_threshold is not None or self._search_type != "similarity_score_threshold":
            self._score_threshold = score_threshold
        if categories is not None:
            self._categories = list(categories) if categories else None
        if neighbor_k is not None:
            self._neighbor_k = max(0, int(neighbor_k))
        if rerank_top_n is not None:
            self._rerank_top_n = rerank_top_n
        if use_rerank is not None:
            prev = self._use_rerank
            self._use_rerank = bool(use_rerank)
            # Load reranker nếu bật mới
            if self._use_rerank and not prev and self._reranker is None:
                self._load_reranker()
        self._rebuild_retriever()

    @property
    def categories(self) -> Optional[list[str]]:
        return list(self._categories) if self._categories else None

    @property
    def search_params(self) -> dict[str, Any]:
        return {
            "top_k": self._top_k,
            "search_type": self._search_type,
            "fetch_k": self._fetch_k,
            "lambda_mult": self._lambda_mult,
            "score_threshold": self._score_threshold,
            "categories": self.categories,
        }

    def _doc_key(self, doc: Document) -> str:
        meta = doc.metadata or {}
        return "|".join(
            [
                str(meta.get("file_path", "")),
                str(meta.get("chunk_index", "")),
                str(meta.get("page_number", "")),
                doc.page_content[:80],
            ]
        )

    def _score_docs(self, question: str, docs: list[Document]) -> list[dict]:
        """Ước lượng relevance score để debug retrieval."""
        if not docs:
            return []

        kwargs = {"k": max(len(docs), self._top_k)}
        flt = self._build_filter(self._categories)
        if flt is not None:
            kwargs["filter"] = flt

        score_lookup: dict[str, float] = {}
        try:
            scored = self.vectorstore.similarity_search_with_relevance_scores(
                question,
                **kwargs,
            )
            for scored_doc, score in scored:
                score_lookup[self._doc_key(scored_doc)] = float(score)
        except Exception:
            score_lookup = {}

        rows: list[dict] = []
        for doc in docs:
            meta = doc.metadata or {}
            rows.append(
                {
                    "score": score_lookup.get(self._doc_key(doc)),
                    "document_name": meta.get("document_name") or meta.get("file_name") or "Không rõ",
                    "page_number": meta.get("page_number"),
                    "chunk_index": meta.get("chunk_index"),
                    "char_count": meta.get("char_count"),
                    "source_url": meta.get("source_url"),
                    "content_preview": (doc.page_content or "")[:300],
                    "metadata": meta,
                    "document": doc,
                }
            )
        return rows

    def ask_with_scores(self, question: str) -> RAGResult:
        """Hỏi và trả về thêm bảng docs kèm score để debug."""
        result = self.ask(question)
        result.docs_with_scores = self._score_docs(question, result.docs)
        return result

    # ── API công khai ────────────────────────────────────────────────────────

    def ask(self, question: str) -> RAGResult:
        """Hỏi 1 câu — retrieve đúng 1 lần và trả lời.

        Pipeline: NFC → retrieve → neighbor expand → rerank → format → LLM
        """
        if not question or not question.strip():
            raise ValueError("Câu hỏi không được rỗng.")
        # 1) Chuẩn hóa Unicode NFC để tránh lỗi so sánh tiếng Việt tổ hợp
        question = unicodedata.normalize("NFC", question)
        # 2) Retrieve
        docs = self.retriever.invoke(question)
        # 3) Neighbor context expansion (nếu bật)
        if self._neighbor_k > 0:
            docs = self._expand_with_neighbors(docs)
        # 4) Rerank (nếu bật)
        if self._use_rerank and self._reranker is not None:
            top_n = self._rerank_top_n if self._rerank_top_n is not None else self._top_k
            docs = self._reranker.rerank(question, docs, top_n=top_n)
        # 5) Format context → LLM
        context = format_docs(docs)
        try:
            answer = self._answer_chain.invoke({"input": question, "context": context})
        except Exception as err:
            answer = self._fallback_and_retry_answer(question, context, err)
        sources = get_unique_sources(docs)
        return RAGResult(answer=answer, sources=sources, docs=docs)

    # Tương thích ngược: cung cấp .invoke giống chain cũ
    def invoke(self, payload: dict) -> str:
        result = self.ask(payload["input"])
        return result.answer


# ── Hàm tiện dụng cho app.py (giữ chữ ký cũ để giảm thay đổi) ────────────────

def load_rag_engine(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
    search_type: str = DEFAULT_SEARCH_TYPE,
    fetch_k: int = DEFAULT_FETCH_K,
    lambda_mult: float = DEFAULT_LAMBDA_MULT,
    score_threshold: Optional[float] = DEFAULT_SCORE_THRESHOLD,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    chroma_dir: str = CHROMA_DIR,
    embed_alias: str = DEFAULT_EMBED_ALIAS,
    chunk_variant: str = DEFAULT_CHUNK_VARIANT,
    chunking_strategy: str = DEFAULT_CHUNKING_STRATEGY,
    categories: Optional[list[str]] = None,
    use_rerank: bool = DEFAULT_USE_RERANK,
    neighbor_k: int = DEFAULT_NEIGHBOR_K,
    rerank_top_n: Optional[int] = DEFAULT_RERANK_TOP_N,
    # Giữ tham số cũ để không phá interface
    groq_api_key: Optional[str] = None,   # noqa: ARG001  (deprecated, ignored)
) -> tuple[RAGEngine, Any, int]:
    """
    Khởi tạo RAG engine.

    Trả về tuple (engine, retriever, doc_count) để tương thích với app.py cũ.

    Args:
        categories  : lọc retriever theo metadata.category (vd ["QD"] hoặc
                      ["QD","TT32_2018"]). None = không lọc.
        use_rerank  : bật BGE Reranker sau retrieval (chậm hơn ~2-3s).
        neighbor_k  : số chunk láng giềng mở rộng (0 = tắt, 1 = ±1 chunk).
        rerank_top_n: số chunk giữ lại sau rerank (None = bằng top_k).
    """
    engine = RAGEngine(
        provider    = provider,
        model       = model_name,
        top_k       = top_k,
        search_type = search_type,
        fetch_k = fetch_k,
        lambda_mult = lambda_mult,
        score_threshold = score_threshold,
        temperature = temperature,
        max_tokens  = max_tokens,
        chroma_dir  = chroma_dir,
        embed_alias = embed_alias,
        chunk_variant = chunk_variant,
        chunking_strategy = chunking_strategy,
        categories  = categories,
        use_rerank  = use_rerank,
        neighbor_k  = neighbor_k,
        rerank_top_n = rerank_top_n,
    )
    return engine, engine.retriever, engine.doc_count


def list_available_collections(chroma_dir: str = CHROMA_DIR) -> list[str]:
    """Liệt kê các collection đang tồn tại trong ChromaDB."""
    chroma_dir = _normalize_chroma_dir(chroma_dir)
    db_path = Path(chroma_dir)
    if not db_path.exists():
        return []
    try:
        return list(_list_available_collections_cached(chroma_dir, _db_signature(chroma_dir)))
    except Exception:
        return []
