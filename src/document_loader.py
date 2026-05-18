"""
document_loader.py
------------------
Load tài liệu và gán metadata đầy đủ cho mọi định dạng được hỗ trợ.

Định dạng hỗ trợ (khớp với SUPPORTED_EXTENSIONS trong config.py):
    .pdf   .docx  .xlsx  .xls   .pptx  .ppt  .txt

Định dạng KHÔNG được index (loại vì gây nhiễu hoặc chất lượng retrieval kém):
    .doc   .csv   .html  .htm   .md

Metadata gán cho MỌI chunk (đảm bảo đồng nhất, không bị thiếu trường):
    document_name  : tên file không có ext   (dùng cho hiển thị / dedupe)
    file_name      : tên file đầy đủ
    file_path      : đường dẫn tương đối từ docs_dir
    file_type      : ext (vd: '.pdf', '.docx')
    file_size_kb   : dung lượng file (KB, làm tròn 1 chữ số)
    source_url     : URL trích dẫn (kèm anchor #page= nếu có)
    page_number    : số trang (chỉ PDF), None với loại khác
    chunk_index    : thứ tự chunk trong tài liệu (1-based)
    total_chunks   : tổng số chunk của tài liệu
    indexed_at     : timestamp ISO 8601
    category       : tên thư mục cha (vd: 'QD', 'TT32_2018', 'root')
    language       : 'vi' (mặc định)
    char_count     : độ dài chunk (số ký tự)

ChromaDB chỉ chấp nhận metadata là str / int / float / bool / None. Tất cả giá trị
được ép kiểu hợp lệ trước khi trả về.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_VARIANTS,
    DEFAULT_LANGUAGE,
    DEFAULT_CHUNK_VARIANT,
    RAW_DOMAIN,
    SUPPORTED_EXTENSIONS,
)


# ── Loader map (lazy import để tránh phụ thuộc cứng) ─────────────────────────

def _load_pdf(path: Path) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader
    return PyMuPDFLoader(str(path)).load()


def _load_docx(path: Path) -> list[Document]:
    from langchain_community.document_loaders import Docx2txtLoader
    return Docx2txtLoader(str(path)).load()


def _load_excel(path: Path) -> list[Document]:
    from langchain_community.document_loaders import UnstructuredExcelLoader
    return UnstructuredExcelLoader(str(path), mode="elements").load()


def _load_ppt(path: Path) -> list[Document]:
    from langchain_community.document_loaders import UnstructuredPowerPointLoader
    return UnstructuredPowerPointLoader(str(path)).load()


def _load_text(path: Path) -> list[Document]:
    from langchain_community.document_loaders import TextLoader
    return TextLoader(str(path), encoding="utf-8", autodetect_encoding=True).load()


# Map ext → (loader function, has_page_metadata)
# Chỉ chứa các định dạng trong SUPPORTED_EXTENSIONS — các định dạng khác
# (.doc, .csv, .html, .htm, .md) không được index vào ChromaDB.
_LOADERS: dict[str, tuple[Any, bool]] = {
    ".pdf" : (_load_pdf,   True),
    ".docx": (_load_docx,  False),
    ".xlsx": (_load_excel, False),
    ".xls" : (_load_excel, False),
    ".pptx": (_load_ppt,   False),
    ".ppt" : (_load_ppt,   False),
    ".txt" : (_load_text,  False),
}


# ── Splitter (tái sử dụng) ────────────────────────────────────────────────────

def make_splitter(
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size     = chunk_size,
        chunk_overlap  = chunk_overlap,
        length_function= len,
        separators     = ["\n\n", "\n", " ", ""],
    )


def make_splitter_from_variant(variant: str = DEFAULT_CHUNK_VARIANT) -> RecursiveCharacterTextSplitter:
    """Tạo splitter theo cấu hình chunk variant."""
    cfg = CHUNK_VARIANTS.get(variant, CHUNK_VARIANTS[DEFAULT_CHUNK_VARIANT])
    return make_splitter(
        chunk_size=int(cfg["chunk_size"]),
        chunk_overlap=int(cfg["chunk_overlap"]),
    )


# ── Metadata helpers ──────────────────────────────────────────────────────────

def _sanitize_metadata(value: Any) -> Any:
    """ChromaDB chỉ chấp nhận str/int/float/bool; các kiểu khác đổi sang str."""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _sanitize_metadata_dict(meta: dict[str, Any]) -> dict[str, Any]:
    """Loại bỏ giá trị None và ép mọi metadata còn lại về kiểu Chroma chấp nhận."""
    return {
        key: _sanitize_metadata(value)
        for key, value in meta.items()
        if value is not None
    }


def _build_source_url(
    base_domain: str,
    rel_path: str,
    page_number: Optional[int],
) -> str:
    """Tạo URL trích dẫn (URL-encoded path).

    Với GitHub blob URL, anchor #page= không được GitHub render trực tiếp nhưng
    vẫn được giữ — tiện cho viewer khác (Google Docs viewer, Mozilla pdf.js, …).
    """
    encoded = quote(rel_path.replace("\\", "/"), safe="/")
    url = f"{base_domain.rstrip('/')}/{encoded}"
    if page_number:
        url += f"#page={page_number}"
    return url


def _build_raw_url(rel_path: str) -> str:
    """URL raw (download/proxy) — không có anchor."""
    encoded = quote(rel_path.replace("\\", "/"), safe="/")
    return f"{RAW_DOMAIN.rstrip('/')}/{encoded}"


def _category_of(file_path: Path, docs_dir: Path) -> str:
    """Lấy thư mục con đầu tiên dưới docs_dir làm category."""
    try:
        rel = file_path.relative_to(docs_dir)
    except ValueError:
        return "root"
    parts = rel.parts
    if len(parts) <= 1:
        return "root"
    return parts[0]


def _shared_file_metadata(
    file_path: Path,
    docs_dir: Path,
    language: str,
) -> dict[str, Any]:
    """Metadata dùng chung cho mọi chiến lược chunking."""
    try:
        rel_path = str(file_path.relative_to(docs_dir)).replace("\\", "/")
    except ValueError:
        rel_path = file_path.name

    return {
        "document_name": file_path.stem,
        "file_name": file_path.name,
        "file_path": rel_path,
        "file_type": file_path.suffix.lower(),
        "file_size_kb": round(file_path.stat().st_size / 1024, 1),
        "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "category": _category_of(file_path, docs_dir),
        "language": language,
    }


def build_chunk_metadata(
    file_path: Path,
    docs_dir: Path,
    base_domain: str,
    chunk_index: int,
    total_chunks: int,
    page_number: Optional[int] = None,
    language: str = DEFAULT_LANGUAGE,
    char_count: Optional[int] = None,
) -> dict[str, Any]:
    """Tạo metadata chuẩn cho một chunk."""
    base = _shared_file_metadata(file_path, docs_dir, language)
    rel_path = base["file_path"]
    source_url = _build_source_url(base_domain, rel_path, page_number)
    raw_url = _build_raw_url(rel_path)
    meta = {
        **base,
        "source_url": source_url,
        "raw_url": raw_url,
        "page_number": page_number,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "char_count": char_count or 0,
    }
    return _sanitize_metadata_dict(meta)


def concat_pages_text(pages: list[Document]) -> str:
    """Ghép toàn bộ page_content thành một text duy nhất để xử lý late chunking."""
    return "\n\n".join((p.page_content or "").strip() for p in pages if (p.page_content or "").strip())


def split_text_with_spans(text: str, splitter: RecursiveCharacterTextSplitter) -> list[tuple[str, tuple[int, int]]]:
    """Tách text và ánh xạ từng chunk về span ký tự trong văn bản gốc."""
    chunks = splitter.split_text(text)
    spans: list[tuple[str, tuple[int, int]]] = []
    cursor = 0

    for chunk in chunks:
        if not chunk:
            continue
        start = text.find(chunk, cursor)
        if start == -1:
            start = text.find(chunk)
        if start == -1:
            continue
        end = start + len(chunk)
        spans.append((chunk, (start, end)))
        cursor = max(cursor, end - 1)

    return spans


# ── API chính ─────────────────────────────────────────────────────────────────

def is_supported(file_path: Path) -> bool:
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def load_documents(file_path: Path) -> tuple[list[Document], bool]:
    """
    Đọc 1 file → (pages, has_page_metadata).
    has_page_metadata=True nếu loader cung cấp 'page' trong metadata (PDF).
    """
    ext = file_path.suffix.lower()
    if ext not in _LOADERS:
        raise ValueError(f"Định dạng không hỗ trợ: {ext}")
    loader_fn, has_page = _LOADERS[ext]
    docs = loader_fn(file_path)
    return docs, has_page


def chunk_file(
    file_path: Path,
    docs_dir: Path,
    base_domain: str,
    splitter: Optional[RecursiveCharacterTextSplitter] = None,
    language: str = DEFAULT_LANGUAGE,
) -> list[Document]:
    """
    Đọc và chunk 1 file, gán metadata đầy đủ cho từng chunk.

    Args:
        file_path  : đường dẫn tới file
        docs_dir   : thư mục gốc (dùng để tính rel_path & category)
        base_domain: domain cho source_url
        splitter   : RecursiveCharacterTextSplitter (auto tạo nếu None)
        language   : mã ngôn ngữ (mặc định 'vi')

    Returns:
        list[Document] — các chunk đã gán metadata.
    """
    if splitter is None:
        splitter = make_splitter()

    pages, has_page = load_documents(file_path)
    if not pages:
        return []

    chunks = splitter.split_documents(pages)
    if not chunks:
        return []

    base_meta    = _shared_file_metadata(file_path, docs_dir, language)
    rel_path     = base_meta["file_path"]
    total_chunks = len(chunks)
    ext          = base_meta["file_type"]

    for idx, chunk in enumerate(chunks, start=1):
        # page chỉ tồn tại với PDF — chuẩn hoá thành int hoặc None
        raw_page = chunk.metadata.get("page") if has_page else None
        page_number: Optional[int]
        if isinstance(raw_page, (int, float)):
            page_number = int(raw_page) + 1   # PyMuPDF zero-based
        else:
            page_number = None

        meta = {
            **base_meta,
            "file_type": ext,
            "source_url": _build_source_url(base_domain, rel_path, page_number),
            "raw_url": _build_raw_url(rel_path),
            "page_number": page_number,
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "char_count": len(chunk.page_content),
        }
        chunk.metadata = _sanitize_metadata_dict(meta)

    return chunks


def scan_docs(
    docs_dir: Path,
    exclude_names: Optional[set[str]] = None,
    exclude_dirs: tuple[str, ...] = ("chroma_db", ".git", "__pycache__", ".venv"),
) -> list[Path]:
    """Quét thư mục, trả về danh sách file hỗ trợ (bỏ qua thư mục build/cache)."""
    if not docs_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục tài liệu: {docs_dir}")

    files: list[Path] = []
    for f in docs_dir.rglob("*"):
        if not f.is_file():
            continue
        if not is_supported(f):
            continue
        # bỏ qua file nằm trong thư mục cần loại
        if any(part in exclude_dirs for part in f.parts):
            continue
        if exclude_names and f.name in exclude_names:
            continue
        files.append(f)
    return sorted(files)
