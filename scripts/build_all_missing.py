"""
build_all_missing.py
--------------------
Build nốt tất cả các combinations Embedding × Chunk variant × Chunking strategy
còn thiếu hoặc rỗng trong ChromaDB, sử dụng smart sync (không rebuild toàn bộ).

Tổng cộng 18 combinations = 2 embeds × 3 chunk variants × 3 chunking strategies.

Chiến lược tối ưu tốc độ:
    - Nhóm theo embedding model → mỗi model chỉ load 1 lần
    - Dùng mode "sync" để chỉ index file mới/thay đổi (bỏ qua file đã index)
    - Bỏ qua collection đã có đủ vectors (không rỗng) trừ khi --force được dùng

Cách dùng:
    python scripts/build_all_missing.py                          # build combinations còn thiếu
    python scripts/build_all_missing.py --dry-run                # chỉ liệt kê, không build
    python scripts/build_all_missing.py --force                  # sync TẤT CẢ 18 combinations
    python scripts/build_all_missing.py --embed bge_m3           # chỉ build 1 embedding
    python scripts/build_all_missing.py --embed bge_m3 minilm    # chỉ build 2 embeddings
    python scripts/build_all_missing.py --skip-late              # bỏ qua late/long_late

Chạy từ thư mục gốc của project:
    cd D:\\02_Work\\Projects\\ChatbotPTCTPT
    python scripts/build_all_missing.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Đảm bảo import được module src/
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import chromadb

from config import (
    CHROMA_DIR,
    CHUNKING_STRATEGIES,
    CHUNK_VARIANTS,
    DEFAULT_DOMAIN,
    DEFAULT_WINDOW_OVERLAP,
    DEFAULT_WINDOW_TOKENS,
    DOCS_DIR,
    EMBED_MODELS,
    build_collection_name,
    get_chunk_params,
    get_embed_model_name,
)
from build_db import mode_sync

DIVIDER = "=" * 72

# Thứ tự ưu tiên embedding (nhẹ → nặng)
EMBED_ORDER = ["minilm", "bge_m3"]


def list_collections(db_dir: str) -> dict[str, int]:
    """Trả về {collection_name: vector_count} từ ChromaDB hiện tại."""
    try:
        client = chromadb.PersistentClient(path=db_dir)
        result = {}
        for col in client.list_collections():
            try:
                result[col.name] = client.get_collection(col.name).count()
            except Exception:
                result[col.name] = 0
        return result
    except Exception as e:
        print(f"Không thể kết nối ChromaDB: {e}")
        return {}


def build_all_combinations() -> list[tuple[str, str, str]]:
    """Trả về danh sách đầy đủ 45 combinations (embed, variant, strategy)."""
    combos = []
    for embed in EMBED_ORDER:
        for variant in CHUNK_VARIANTS:
            for strategy in CHUNKING_STRATEGIES:
                combos.append((embed, variant, strategy))
    return combos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build nốt các combinations ChromaDB còn thiếu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Chỉ liệt kê, không thực sự build",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Sync TẤT CẢ 45 combinations, kể cả đã có dữ liệu",
    )
    parser.add_argument(
        "--embed", nargs="*", choices=list(EMBED_MODELS.keys()),
        help="Chỉ build embedding model cụ thể (ví dụ: --embed bge_m3 minilm)",
    )
    parser.add_argument(
        "--skip-late", action="store_true",
        help="Bỏ qua các strategy late và long_late",
    )
    parser.add_argument(
        "--docs-dir", default=DOCS_DIR,
        help=f"Thư mục tài liệu nguồn (mặc định: {DOCS_DIR})",
    )
    parser.add_argument(
        "--db-dir", default=CHROMA_DIR,
        help=f"Thư mục ChromaDB (mặc định: {CHROMA_DIR})",
    )
    parser.add_argument(
        "--domain", default=DEFAULT_DOMAIN,
        help="Domain cho source URL",
    )
    parser.add_argument(
        "--window-tokens", type=int, default=DEFAULT_WINDOW_TOKENS,
    )
    parser.add_argument(
        "--window-overlap", type=int, default=DEFAULT_WINDOW_OVERLAP,
    )
    args = parser.parse_args()

    print(f"\n{DIVIDER}")
    print("   BUILD ALL MISSING — ChatbotPTCTPT")
    print(DIVIDER)
    print(f"Tài liệu    : {args.docs_dir}")
    print(f"Database    : {args.db_dir}")
    print(f"Force sync  : {args.force}")
    print(f"Dry run     : {args.dry_run}")
    print(DIVIDER)

    # ── Lấy danh sách collections hiện có ────────────────────────────────────
    existing = list_collections(args.db_dir)
    print(f"\nCollections hiện có trong DB: {len(existing)}")
    for name, count in sorted(existing.items()):
        print(f"  {name:<45} {count:>8,} vectors")

    # ── Xác định combinations cần build ──────────────────────────────────────
    all_combos = build_all_combinations()
    to_build: list[tuple[str, str, str]] = []

    embed_filter = set(args.embed) if args.embed else None

    for embed, variant, strategy in all_combos:
        # Filter theo --embed
        if embed_filter and embed not in embed_filter:
            continue
        # Filter late strategies
        if args.skip_late and strategy in {"late", "long_late"}:
            continue

        col_name = build_collection_name(embed, variant, strategy)
        vector_count = existing.get(col_name, -1)   # -1 = chưa tồn tại

        if args.force:
            to_build.append((embed, variant, strategy))
        elif vector_count <= 0:
            # Missing (không tồn tại) hoặc rỗng
            to_build.append((embed, variant, strategy))

    print(f"\nCombinations cần build: {len(to_build)}/{len(all_combos)}")

    if not to_build:
        print("\nTất cả combinations đã có dữ liệu. Dùng --force để sync lại.")
        print(DIVIDER)
        return

    print(f"\n{'#':<3} {'Combination':<45} {'Status'}")
    print("-" * 60)
    for i, (embed, variant, strategy) in enumerate(to_build, 1):
        col_name = build_collection_name(embed, variant, strategy)
        count = existing.get(col_name, -1)
        status = "rỗng" if count == 0 else "chưa tạo"
        print(f"{i:<3} {col_name:<45} {status}")

    if args.dry_run:
        print(f"\n[DRY RUN] Không thực sự build. Tổng: {len(to_build)} combinations.")
        print(DIVIDER)
        return

    # ── Nhóm theo embedding model (để load model 1 lần duy nhất) ─────────────
    # to_build đã được sắp xếp theo EMBED_ORDER (vì build_all_combinations dùng thứ tự đó)
    # và embed_filter không phá vỡ thứ tự → các combinations cùng embed kề nhau

    total = len(to_build)
    done = 0
    errors = 0

    print(f"\n{DIVIDER}")
    print("BẮT ĐẦU BUILD")
    print(DIVIDER)

    start_total = time.time()
    current_embed = None

    for idx, (embed, variant, strategy) in enumerate(to_build, 1):
        col_name = build_collection_name(embed, variant, strategy)

        if embed != current_embed:
            current_embed = embed
            model_name = get_embed_model_name(embed)
            print(f"\n{'─'*60}")
            print(f"Embedding model: {embed} → {model_name}")
            print(f"{'─'*60}")

        _, chunk_size, chunk_overlap = get_chunk_params(variant)
        print(f"\n[{idx}/{total}] {col_name}")
        print(f"       variant={variant} ({chunk_size}/{chunk_overlap}), strategy={strategy}")

        t0 = time.time()
        try:
            mode_sync(
                docs_dir=args.docs_dir,
                db_dir=args.db_dir,
                domain=args.domain,
                embed_alias=embed,
                chunk_variant=variant,
                chunking_strategy=strategy,
                window_tokens=args.window_tokens,
                window_overlap=args.window_overlap,
            )
            elapsed = time.time() - t0
            print(f"       ✓ Hoàn thành trong {elapsed:.1f}s")
            done += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"       ✗ Lỗi: {e} (sau {elapsed:.1f}s)")
            errors += 1

    total_elapsed = time.time() - start_total
    m, s = divmod(int(total_elapsed), 60)

    print(f"\n{DIVIDER}")
    print("KẾT QUẢ BUILD ALL MISSING")
    print(DIVIDER)
    print(f"Tổng combinations : {total}")
    print(f"Thành công        : {done}")
    print(f"Lỗi               : {errors}")
    print(f"Thời gian         : {m}m {s}s")
    print(DIVIDER)

    # In thống kê cuối
    final = list_collections(args.db_dir)
    print(f"\nCollections sau khi build: {len(final)}")
    for name, count in sorted(final.items()):
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {name:<45} {count:>8,} vectors")
    print(DIVIDER)


if __name__ == "__main__":
    main()
