"""CLI build and maintenance tool for ChromaDB collections."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import (
    BATCH_SIZE,
    CHROMA_DIR,
    CHUNKING_STRATEGIES,
    CHUNK_VARIANTS,
    DEFAULT_CHUNKING_STRATEGY,
    DEFAULT_CHUNK_VARIANT,
    DEFAULT_DOMAIN,
    DEFAULT_EMBED_ALIAS,
    DEFAULT_WINDOW_OVERLAP,
    DEFAULT_WINDOW_TOKENS,
    DOCS_DIR,
    EMBED_MODELS,
    SUPPORTED_EXTENSIONS,
    build_collection_name,
    get_chunk_params,
    get_chunking_strategy,
    get_embed_alias,
    get_embed_model_name,
)
from document_loader import (
    build_chunk_metadata,
    chunk_file,
    concat_pages_text,
    load_documents,
    make_splitter,
    scan_docs,
    split_text_with_spans,
)
from late_chunking import LateChunkingEmbedder

DIVIDER = "=" * 72


def _registry_path(db_dir: str, collection_name: str) -> Path:
    return Path(db_dir) / f"indexed_files__{collection_name}.json"


def load_registry(db_dir: str, collection_name: str) -> dict:
    p = _registry_path(db_dir, collection_name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Khong doc duoc registry ({e}), tao moi.")
    return {}


def save_registry(db_dir: str, collection_name: str, registry: dict) -> None:
    p = _registry_path(db_dir, collection_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _add_to_registry(registry: dict, file_path: Path, docs_dir: Path, chunk_count: int, category: str) -> None:
    try:
        rel = str(file_path.relative_to(docs_dir)).replace("\\", "/")
    except ValueError:
        rel = file_path.name

    stat = file_path.stat()
    registry[file_path.name] = {
        "stem": file_path.stem,
        "file_name": file_path.name,
        "file_path": rel,
        "file_type": file_path.suffix.lower(),
        "category": category,
        "indexed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_count": chunk_count,
        "size_kb": round(stat.st_size / 1024, 1),
        "file_mtime": round(stat.st_mtime, 3),
    }


def get_embeddings(embed_alias: str) -> HuggingFaceEmbeddings:
    model_name = get_embed_model_name(embed_alias)
    print(f"Embedding model: {embed_alias} -> {model_name}")
    return HuggingFaceEmbeddings(
        model_name=model_name,
        encode_kwargs={"batch_size": 64, "show_progress_bar": False},
    )


def _new_vectorstore(db_dir: str, collection_name: str, embeddings: HuggingFaceEmbeddings) -> Chroma:
    return Chroma(
        persist_directory=db_dir,
        embedding_function=embeddings,
        collection_name=collection_name,
    )


def _delete_collection(db_dir: str, collection_name: str) -> None:
    try:
        client = chromadb.PersistentClient(path=db_dir)
        names = {c.name for c in client.list_collections()}
        if collection_name in names:
            client.delete_collection(collection_name)
            print(f"Da xoa collection cu: {collection_name}")
    except Exception as e:
        print(f"Khong xoa duoc collection {collection_name}: {e}")


def _add_chunks_with_embeddings(
    vectorstore: Chroma,
    texts: list[str],
    metadatas: list[dict],
    embeddings: list[list[float]],
) -> None:
    total = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(texts), BATCH_SIZE):
        chunk_texts = texts[i : i + BATCH_SIZE]
        chunk_meta = metadatas[i : i + BATCH_SIZE]
        chunk_emb = embeddings[i : i + BATCH_SIZE]
        ids = [str(uuid.uuid4()) for _ in chunk_texts]
        n = i // BATCH_SIZE + 1
        print(f"     Batch {n}/{total} ({len(chunk_texts)} chunks)")
        vectorstore._collection.add(
            ids=ids,
            documents=chunk_texts,
            metadatas=chunk_meta,
            embeddings=chunk_emb,
        )


def _build_standard_chunks(
    file_path: Path,
    docs_root: Path,
    domain: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list:
    splitter = make_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunk_file(file_path, docs_root, domain, splitter)


def _build_late_chunk_payload(
    file_path: Path,
    docs_root: Path,
    domain: str,
    chunk_size: int,
    chunk_overlap: int,
    embedder: LateChunkingEmbedder,
) -> tuple[list[str], list[dict], list[list[float]]]:
    splitter = make_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pages, _ = load_documents(file_path)
    full_text = concat_pages_text(pages)
    if not full_text.strip():
        return [], [], []

    chunk_items = split_text_with_spans(full_text, splitter)
    if not chunk_items:
        return [], [], []

    texts = [item[0] for item in chunk_items]
    spans = [item[1] for item in chunk_items]
    vectors = embedder.embed_document_chunks(full_text, spans)

    if len(vectors) != len(texts):
        return [], [], []

    total_chunks = len(texts)
    metadatas: list[dict] = []
    for i, text in enumerate(texts, start=1):
        meta = build_chunk_metadata(
            file_path=file_path,
            docs_dir=docs_root,
            base_domain=domain,
            chunk_index=i,
            total_chunks=total_chunks,
            page_number=None,
            char_count=len(text),
        )
        metadatas.append(meta)

    return texts, metadatas, vectors


def mode_rebuild(
    docs_dir: str,
    db_dir: str,
    domain: str,
    force: bool,
    embed_alias: str,
    chunk_variant: str,
    chunking_strategy: str,
    window_tokens: int,
    window_overlap: int,
) -> None:
    docs_root = Path(docs_dir)
    collection_name = build_collection_name(embed_alias, chunk_variant, chunking_strategy)

    if not force:
        ans = input(
            f"Rebuild collection '{collection_name}'? Du lieu cu se bi ghi de. [yes/N]: "
        ).strip().lower()
        if ans != "yes":
            print("Da huy.")
            return

    Path(db_dir).mkdir(parents=True, exist_ok=True)
    _delete_collection(db_dir, collection_name)

    reg_path = _registry_path(db_dir, collection_name)
    if reg_path.exists():
        reg_path.unlink(missing_ok=True)

    target_files = scan_docs(docs_root)
    if not target_files:
        print("Khong tim thay tai lieu nao.")
        return

    print(f"Tim thay {len(target_files)} file. Bat dau xu ly...\n")

    embeddings = get_embeddings(embed_alias)
    vectorstore = _new_vectorstore(db_dir, collection_name, embeddings)

    _, chunk_size, chunk_overlap = get_chunk_params(chunk_variant)
    use_late = chunking_strategy in {"late", "long_late"}
    late_embedder = None
    if use_late:
        late_embedder = LateChunkingEmbedder(
            model_name=get_embed_model_name(embed_alias),
            window_tokens=window_tokens,
            window_overlap=window_overlap,
        )

    registry: dict = {}
    success = 0
    skipped = 0

    if use_late and late_embedder is not None:
        # Late / Long-Late: embed per-document (each doc is an independent context window)
        for file_path in target_files:
            print(f"  {file_path.name}", end=" ... ")
            try:
                texts, metadatas, vectors = _build_late_chunk_payload(
                    file_path=file_path,
                    docs_root=docs_root,
                    domain=domain,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    embedder=late_embedder,
                )
                if not texts:
                    print("bo qua (rong)")
                    skipped += 1
                    continue
                _add_chunks_with_embeddings(vectorstore, texts, metadatas, vectors)
                category = metadatas[0].get("category", "root")
                _add_to_registry(registry, file_path, docs_root, len(texts), category)
                success += 1
                print(f"xong ({len(texts)} chunks)")
            except Exception as e:
                print(f"loi: {e}")
    else:
        # Standard: Phase 1 — load + split all files (no embedding yet)
        file_chunks: list[tuple[Path, list]] = []
        for file_path in target_files:
            print(f"  [load] {file_path.name}", end=" ... ")
            try:
                chunks = _build_standard_chunks(
                    file_path=file_path,
                    docs_root=docs_root,
                    domain=domain,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                if not chunks:
                    print("bo qua (rong)")
                    skipped += 1
                    continue
                file_chunks.append((file_path, chunks))
                print(f"ok ({len(chunks)} chunks)")
            except Exception as e:
                print(f"loi: {e}")

        # Standard: Phase 2 — bulk embed + insert all chunks in large batches
        all_chunks = [c for _, chunks in file_chunks for c in chunks]
        n_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n  Embedding {len(all_chunks)} chunks tong cong ({n_batches} batch)...")
        for i in range(0, len(all_chunks), BATCH_SIZE):
            batch = all_chunks[i : i + BATCH_SIZE]
            nb = i // BATCH_SIZE + 1
            print(f"     Batch {nb}/{n_batches} ({len(batch)} chunks)")
            vectorstore.add_documents(batch)

        # Standard: Phase 3 — update registry per file
        for file_path, chunks in file_chunks:
            category = chunks[0].metadata.get("category", "root")
            _add_to_registry(registry, file_path, docs_root, len(chunks), category)
            success += 1

    save_registry(db_dir, collection_name, registry)
    count = vectorstore._collection.count()

    print(f"\n{DIVIDER}")
    print("REBUILD HOAN TAT")
    print(f"Collection      : {collection_name}")
    print(f"File thanh cong : {success}/{len(target_files)} (bo qua {skipped})")
    print(f"Tong vectors    : {count:,}")
    print(f"Luu tai         : {db_dir}")
    print(DIVIDER)


def mode_add(
    docs_dir: str,
    db_dir: str,
    domain: str,
    specific_file: Optional[str],
    embed_alias: str,
    chunk_variant: str,
    chunking_strategy: str,
    window_tokens: int,
    window_overlap: int,
) -> None:
    docs_root = Path(docs_dir)
    collection_name = build_collection_name(embed_alias, chunk_variant, chunking_strategy)

    Path(db_dir).mkdir(parents=True, exist_ok=True)
    embeddings = get_embeddings(embed_alias)
    vectorstore = _new_vectorstore(db_dir, collection_name, embeddings)
    before_count = vectorstore._collection.count()

    registry = load_registry(db_dir, collection_name)

    if specific_file:
        found = [f for f in docs_root.rglob(specific_file) if "chroma_db" not in f.parts]
        if not found:
            print(f"Khong tim thay file '{specific_file}' trong {docs_dir}")
            return
        if specific_file in registry:
            print(f"'{specific_file}' da index, xoa chunks cu va index lai...")
            _delete_by_document_name(vectorstore, Path(specific_file).stem)
            del registry[specific_file]
        target_files = found
    else:
        all_files = scan_docs(docs_root)
        indexed = set(registry.keys())
        target_files = [f for f in all_files if f.name not in indexed]
        if not target_files:
            print("Khong co file moi.")
            return

    _, chunk_size, chunk_overlap = get_chunk_params(chunk_variant)
    use_late = chunking_strategy in {"late", "long_late"}
    late_embedder = None
    if use_late:
        late_embedder = LateChunkingEmbedder(
            model_name=get_embed_model_name(embed_alias),
            window_tokens=window_tokens,
            window_overlap=window_overlap,
        )

    print(f"Tim thay {len(target_files)} file can them:\n")
    success = 0

    for file_path in target_files:
        print(f"  + {file_path.name}", end=" ... ")
        try:
            if use_late and late_embedder is not None:
                texts, metadatas, vectors = _build_late_chunk_payload(
                    file_path=file_path,
                    docs_root=docs_root,
                    domain=domain,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    embedder=late_embedder,
                )
                if not texts:
                    print("bo qua (rong)")
                    continue
                _add_chunks_with_embeddings(vectorstore, texts, metadatas, vectors)
                category = metadatas[0].get("category", "root")
                _add_to_registry(registry, file_path, docs_root, len(texts), category)
                success += 1
                print(f"xong ({len(texts)} chunks)")
            else:
                chunks = _build_standard_chunks(
                    file_path=file_path,
                    docs_root=docs_root,
                    domain=domain,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                if not chunks:
                    print("bo qua (rong)")
                    continue
                total = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
                for i in range(0, len(chunks), BATCH_SIZE):
                    batch = chunks[i : i + BATCH_SIZE]
                    n = i // BATCH_SIZE + 1
                    print(f"     Batch {n}/{total} ({len(batch)} chunks)")
                    vectorstore.add_documents(batch)
                category = chunks[0].metadata.get("category", "root")
                _add_to_registry(registry, file_path, docs_root, len(chunks), category)
                success += 1
                print(f"xong ({len(chunks)} chunks)")
        except Exception as e:
            print(f"loi: {e}")

    save_registry(db_dir, collection_name, registry)
    after_count = vectorstore._collection.count()

    print(f"\n{DIVIDER}")
    print("ADD HOAN TAT")
    print(f"Collection      : {collection_name}")
    print(f"File them moi   : {success}/{len(target_files)}")
    print(f"Vectors truoc   : {before_count:,}")
    print(f"Vectors sau     : {after_count:,}")
    print(f"Tang them       : +{after_count - before_count:,}")
    print(DIVIDER)


def _delete_by_document_name(vectorstore: Chroma, doc_stem: str) -> int:
    try:
        results = vectorstore._collection.get(
            where={"document_name": {"$eq": doc_stem}},
            include=[],
        )
        ids = results.get("ids", [])
        if ids:
            vectorstore._collection.delete(ids=ids)
            print(f"  Da xoa {len(ids)} chunks cua '{doc_stem}'")
        return len(ids)
    except Exception as e:
        print(f"  Loi khi xoa: {e}")
        return 0


def mode_remove(db_dir: str, specific_file: Optional[str], embed_alias: str, chunk_variant: str, chunking_strategy: str) -> None:
    if not specific_file:
        print("Can chi dinh ten file voi --file, vi du: --file TT22.pdf")
        return

    collection_name = build_collection_name(embed_alias, chunk_variant, chunking_strategy)
    embeddings = get_embeddings(embed_alias)
    vectorstore = _new_vectorstore(db_dir, collection_name, embeddings)

    registry = load_registry(db_dir, collection_name)
    before_count = vectorstore._collection.count()
    deleted = _delete_by_document_name(vectorstore, Path(specific_file).stem)

    if specific_file in registry:
        del registry[specific_file]
        save_registry(db_dir, collection_name, registry)

    after_count = vectorstore._collection.count()
    print(f"\n{DIVIDER}")
    if deleted > 0:
        print("REMOVE HOAN TAT")
        print(f"Collection      : {collection_name}")
        print(f"Van ban xoa     : {specific_file}")
        print(f"Vectors xoa     : {deleted:,}")
        print(f"Vectors con lai : {after_count:,}")
    else:
        print(f"Khong tim thay chunks cua '{specific_file}' trong {collection_name}.")
        print(f"Vectors hien tai: {before_count:,}")
    print(DIVIDER)


def mode_sync(
    docs_dir: str,
    db_dir: str,
    domain: str,
    embed_alias: str,
    chunk_variant: str,
    chunking_strategy: str,
    window_tokens: int,
    window_overlap: int,
) -> None:
    """So sanh DB voi thu muc tai lieu roi dong bo hoa:
    - Xoa chunks cua file da bi xoa khoi data/
    - Cap nhat lai chunks cua file da bi thay doi tren disk
    - Them chunks cua file moi chua duoc index
    - Bo qua file da index va khong co gi thay doi
    """
    docs_root = Path(docs_dir)
    collection_name = build_collection_name(embed_alias, chunk_variant, chunking_strategy)
    Path(db_dir).mkdir(parents=True, exist_ok=True)

    registry = load_registry(db_dir, collection_name)

    # ── So sanh registry <> disk ──────────────────────────────────────────────
    current_files    = scan_docs(docs_root)
    current_by_name  = {f.name: f for f in current_files}
    indexed_names    = set(registry.keys())
    current_names    = set(current_by_name.keys())

    deleted_names = indexed_names - current_names          # mat khoi disk
    new_names     = current_names - indexed_names          # chua co trong DB

    # File co trong ca hai — kiem tra xem co thay doi khong
    modified_names: set[str] = set()
    for name in indexed_names & current_names:
        f   = current_by_name[name]
        reg = registry[name]
        reg_mtime = reg.get("file_mtime")
        cur_mtime = round(f.stat().st_mtime, 3)
        if reg_mtime is not None:
            if abs(float(reg_mtime) - cur_mtime) > 1.0:
                modified_names.add(name)
        else:
            # Legacy entry (khong co file_mtime) — fallback sang size_kb
            reg_size = reg.get("size_kb")
            cur_size = round(f.stat().st_size / 1024, 1)
            if reg_size is not None and abs(float(reg_size) - cur_size) > 0.1:
                modified_names.add(name)

    unchanged_count = len(indexed_names & current_names) - len(modified_names)

    print(f"  Ket qua so sanh registry <> disk:")
    print(f"    Khong doi (bo qua)      : {unchanged_count}")
    print(f"    Bi xoa khoi disk        : {len(deleted_names)}")
    print(f"    Moi chua index          : {len(new_names)}")
    print(f"    Thay doi (se cap nhat)  : {len(modified_names)}")

    if not deleted_names and not new_names and not modified_names:
        print("\n  Collection da dong bo. Khong co thay doi.")
        return

    embeddings  = get_embeddings(embed_alias)
    vectorstore = _new_vectorstore(db_dir, collection_name, embeddings)
    before_count = vectorstore._collection.count()

    # ── Buoc 1: Xoa chunks cua file mat khoi disk ─────────────────────────────
    n_removed = 0
    if deleted_names:
        print(f"\n  Xoa chunks cua {len(deleted_names)} file da mat khoi disk...")
        for name in sorted(deleted_names):
            n = _delete_by_document_name(vectorstore, Path(name).stem)
            del registry[name]
            if n > 0:
                n_removed += 1

    # ── Buoc 2: Xoa chunks cu cua file thay doi (index lai o buoc 3) ──────────
    if modified_names:
        print(f"\n  Xoa chunks cu cua {len(modified_names)} file thay doi...")
        for name in sorted(modified_names):
            _delete_by_document_name(vectorstore, Path(name).stem)
            del registry[name]

    # ── Buoc 3: Them file moi + file vua thay doi ─────────────────────────────
    to_add: list[Path] = sorted(
        [current_by_name[n] for n in (new_names | modified_names) if n in current_by_name],
        key=lambda p: p.name,
    )

    n_new_success      = 0
    n_updated_success  = 0

    if to_add:
        _, chunk_size, chunk_overlap = get_chunk_params(chunk_variant)
        use_late = chunking_strategy in {"late", "long_late"}

        if use_late:
            late_embedder = LateChunkingEmbedder(
                model_name=get_embed_model_name(embed_alias),
                window_tokens=window_tokens,
                window_overlap=window_overlap,
            )
            print(f"\n  Dang them/cap nhat {len(to_add)} file (late chunking)...")
            for file_path in to_add:
                print(f"    + {file_path.name}", end=" ... ")
                try:
                    texts, metadatas, vectors = _build_late_chunk_payload(
                        file_path=file_path,
                        docs_root=docs_root,
                        domain=domain,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        embedder=late_embedder,
                    )
                    if not texts:
                        print("bo qua (rong)")
                        continue
                    _add_chunks_with_embeddings(vectorstore, texts, metadatas, vectors)
                    category = metadatas[0].get("category", "root")
                    _add_to_registry(registry, file_path, docs_root, len(texts), category)
                    if file_path.name in modified_names:
                        n_updated_success += 1
                    else:
                        n_new_success += 1
                    print(f"xong ({len(texts)} chunks)")
                except Exception as e:
                    print(f"loi: {e}")

        else:
            # Phase 1 — load + split tat ca file (chua embed)
            print(f"\n  [load] {len(to_add)} file can xu ly...")
            file_chunks: list[tuple[Path, list]] = []
            for file_path in to_add:
                print(f"    [load] {file_path.name}", end=" ... ")
                try:
                    chunks = _build_standard_chunks(
                        file_path=file_path,
                        docs_root=docs_root,
                        domain=domain,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    if not chunks:
                        print("bo qua (rong)")
                        continue
                    file_chunks.append((file_path, chunks))
                    print(f"ok ({len(chunks)} chunks)")
                except Exception as e:
                    print(f"loi: {e}")

            # Phase 2 — bulk embed + insert
            if file_chunks:
                all_chunks = [c for _, cs in file_chunks for c in cs]
                n_batches  = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"\n    Embedding {len(all_chunks)} chunks ({n_batches} batch)...")
                for i in range(0, len(all_chunks), BATCH_SIZE):
                    batch = all_chunks[i : i + BATCH_SIZE]
                    nb = i // BATCH_SIZE + 1
                    print(f"      Batch {nb}/{n_batches} ({len(batch)} chunks)")
                    vectorstore.add_documents(batch)

                # Phase 3 — cap nhat registry
                for file_path, chunks in file_chunks:
                    category = chunks[0].metadata.get("category", "root")
                    _add_to_registry(registry, file_path, docs_root, len(chunks), category)
                    if file_path.name in modified_names:
                        n_updated_success += 1
                    else:
                        n_new_success += 1

    save_registry(db_dir, collection_name, registry)
    after_count = vectorstore._collection.count()

    print(f"\n{DIVIDER}")
    print("SYNC HOAN TAT")
    print(f"Collection      : {collection_name}")
    print(f"Khong doi       : {unchanged_count}")
    print(f"Xoa (mat file)  : {n_removed}")
    print(f"Them moi        : {n_new_success}")
    print(f"Cap nhat lai    : {n_updated_success}")
    print(f"Vectors truoc   : {before_count:,}")
    print(f"Vectors sau     : {after_count:,}")
    print(DIVIDER)


def _collection_stats(client: chromadb.PersistentClient, collection_name: str) -> tuple[int, Optional[dict]]:
    try:
        col = client.get_collection(collection_name)
        return col.count(), col
    except Exception:
        return 0, None


def mode_status(db_dir: str, embed_alias: Optional[str], chunk_variant: Optional[str], chunking_strategy: Optional[str]) -> None:
    db_path = Path(db_dir)
    if not db_path.exists():
        print(f"Database chua ton tai tai '{db_dir}'.")
        return

    client = chromadb.PersistentClient(path=db_dir)
    collections = sorted(c.name for c in client.list_collections())

    print(f"\n{DIVIDER}")
    print("THONG KE DATABASE")
    print(DIVIDER)
    print(f"Thu muc: {db_dir}")

    if embed_alias or chunk_variant or chunking_strategy:
        emb = get_embed_alias(embed_alias)
        var = chunk_variant if chunk_variant in CHUNK_VARIANTS else DEFAULT_CHUNK_VARIANT
        strat = get_chunking_strategy(chunking_strategy)
        target = build_collection_name(emb, var, strat)
        vectors, _ = _collection_stats(client, target)
        print(f"Collection muc tieu: {target}")
        print(f"Tong vectors       : {vectors:,}")
        registry = load_registry(db_dir, target)
        print(f"So van ban         : {len(registry)}")
        print(DIVIDER)
        return

    if not collections:
        print("Chua co collection nao.")
        print(DIVIDER)
        return

    print(f"Tong collections: {len(collections)}")
    print("\n#  Collection                                 Vectors   Files")
    print("-" * 72)
    for idx, name in enumerate(collections, start=1):
        vectors, _ = _collection_stats(client, name)
        registry = load_registry(db_dir, name)
        print(f"{idx:<2} {name:<42} {vectors:>8,} {len(registry):>7}")

    print(DIVIDER)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quan ly ChromaDB cho ChatbotPTCTPT (multi-collection)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Vi du:\n"
            "  python src/build_db.py --mode rebuild --force\n"
            "  python src/build_db.py --mode rebuild --embed-model bge_m3 --chunk-variant balanced --chunking-strategy long_late --force\n"
            "  python src/build_db.py --mode add --file TT22.pdf\n"
            "  python src/build_db.py --mode sync --embed-model bge_m3 --chunk-variant balanced --chunking-strategy long_late\n"
            "  python src/build_db.py --mode status\n"
        ),
    )

    parser.add_argument("--mode", choices=["rebuild", "add", "remove", "sync", "status"], default="rebuild")
    parser.add_argument("--docs_dir", default=DOCS_DIR, help="Thu muc chua tai lieu")
    parser.add_argument("--db_dir", default=CHROMA_DIR, help="Thu muc luu database")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Domain cho source URL")
    parser.add_argument("--force", action="store_true", help="Rebuild khong hoi xac nhan")
    parser.add_argument("--file", default=None, help="Ten file (dung voi add/remove)")

    parser.add_argument("--embed-model", choices=sorted(EMBED_MODELS.keys()), default=DEFAULT_EMBED_ALIAS)
    parser.add_argument("--chunk-variant", choices=sorted(CHUNK_VARIANTS.keys()), default=DEFAULT_CHUNK_VARIANT)
    parser.add_argument("--chunking-strategy", choices=sorted(CHUNKING_STRATEGIES.keys()), default=DEFAULT_CHUNKING_STRATEGY)
    parser.add_argument("--window-tokens", type=int, default=DEFAULT_WINDOW_TOKENS)
    parser.add_argument("--window-overlap", type=int, default=DEFAULT_WINDOW_OVERLAP)

    args = parser.parse_args()

    embed_alias = get_embed_alias(args.embed_model)
    chunk_variant, chunk_size, chunk_overlap = get_chunk_params(args.chunk_variant)
    chunking_strategy = get_chunking_strategy(args.chunking_strategy)
    collection_name = build_collection_name(embed_alias, chunk_variant, chunking_strategy)

    print(f"\n{DIVIDER}")
    print(f"   BUILD_DB - ChatbotPTCTPT  [{args.mode.upper()}]")
    print(DIVIDER)
    print(f"Embedding alias : {embed_alias}")
    print(f"Chunk variant   : {chunk_variant} ({chunk_size}/{chunk_overlap})")
    print(f"Strategy        : {chunking_strategy}")
    print(f"Collection      : {collection_name}")
    if chunking_strategy in {"late", "long_late"}:
        print(f"Window tokens   : {args.window_tokens}")
        print(f"Window overlap  : {args.window_overlap}")
    if args.mode != "status":
        print(f"Tai lieu        : {args.docs_dir}")
        print(f"Database        : {args.db_dir}")
        if args.mode in ("rebuild", "add", "sync"):
            print(f"Domain          : {args.domain}")
            print(f"Dinh dang       : {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        if args.file:
            print(f"File            : {args.file}")
    print(f"{DIVIDER}\n")

    if args.mode == "rebuild":
        mode_rebuild(
            docs_dir=args.docs_dir,
            db_dir=args.db_dir,
            domain=args.domain,
            force=args.force,
            embed_alias=embed_alias,
            chunk_variant=chunk_variant,
            chunking_strategy=chunking_strategy,
            window_tokens=args.window_tokens,
            window_overlap=args.window_overlap,
        )
    elif args.mode == "add":
        mode_add(
            docs_dir=args.docs_dir,
            db_dir=args.db_dir,
            domain=args.domain,
            specific_file=args.file,
            embed_alias=embed_alias,
            chunk_variant=chunk_variant,
            chunking_strategy=chunking_strategy,
            window_tokens=args.window_tokens,
            window_overlap=args.window_overlap,
        )
    elif args.mode == "remove":
        mode_remove(
            db_dir=args.db_dir,
            specific_file=args.file,
            embed_alias=embed_alias,
            chunk_variant=chunk_variant,
            chunking_strategy=chunking_strategy,
        )
    elif args.mode == "sync":
        mode_sync(
            docs_dir=args.docs_dir,
            db_dir=args.db_dir,
            domain=args.domain,
            embed_alias=embed_alias,
            chunk_variant=chunk_variant,
            chunking_strategy=chunking_strategy,
            window_tokens=args.window_tokens,
            window_overlap=args.window_overlap,
        )
    elif args.mode == "status":
        mode_status(
            db_dir=args.db_dir,
            embed_alias=args.embed_model,
            chunk_variant=args.chunk_variant,
            chunking_strategy=args.chunking_strategy,
        )


if __name__ == "__main__":
    main()
