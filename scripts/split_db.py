"""
split_db.py — Chia nhỏ chroma.sqlite3 thành các phần <49 MB để push GitHub.

Chạy SAU KHI build_all_variants.cmd hoàn chỉnh:
    python scripts/split_db.py

Output: chroma_db/chroma.sqlite3.part.000, .001, .002, ...
File gốc chroma.sqlite3 được GIỮ NGUYÊN (không xóa).

Để reassemble thủ công (nếu cần):
    python scripts/split_db.py --reassemble
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
SQLITE    = ROOT / "chroma_db" / "chroma.sqlite3"
PART_SIZE = 48 * 1024 * 1024   # 48 MB — an toàn dưới giới hạn 50 MB GitHub


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split(src: Path = SQLITE, part_size: int = PART_SIZE) -> None:
    if not src.exists():
        print(f"[split_db] ERROR: không tìm thấy {src}")
        sys.exit(1)

    total = src.stat().st_size
    n_parts = (total + part_size - 1) // part_size
    print(f"[split_db] {src.name}  {total / 1024**2:.1f} MB  →  {n_parts} phần")

    # Xóa các part cũ
    for old in sorted(src.parent.glob(f"{src.name}.part.*")):
        old.unlink()

    checksum = md5(src)
    with open(src, "rb") as f:
        idx = 0
        while True:
            data = f.read(part_size)
            if not data:
                break
            part_path = src.parent / f"{src.name}.part.{idx:03d}"
            part_path.write_bytes(data)
            print(f"  {part_path.name}  {len(data) / 1024**2:.1f} MB")
            idx += 1

    # Ghi checksum để verify khi reassemble
    (src.parent / f"{src.name}.md5").write_text(checksum)
    print(f"\n[split_db] ✓ Xong — MD5: {checksum}")
    print(f"[split_db] Nhớ thêm vào .gitignore: chroma_db/chroma.sqlite3")
    print(f"[split_db] Và BỎ ignore: chroma_db/chroma.sqlite3.part.*")


def reassemble(src: Path = SQLITE) -> None:
    parts = sorted(src.parent.glob(f"{src.name}.part.*"))
    if not parts:
        print(f"[split_db] Không tìm thấy part nào — bỏ qua reassemble.")
        return

    if src.exists():
        print(f"[split_db] {src.name} đã tồn tại — bỏ qua reassemble.")
        return

    print(f"[split_db] Đang ghép {len(parts)} phần → {src.name} ...")
    with open(src, "wb") as out:
        for part in parts:
            out.write(part.read_bytes())

    # Verify checksum nếu có
    md5_file = src.parent / f"{src.name}.md5"
    if md5_file.exists():
        expected = md5_file.read_text().strip()
        actual   = md5(src)
        if actual != expected:
            src.unlink()
            print(f"[split_db] ERROR: checksum không khớp! File bị xóa.")
            sys.exit(1)
        print(f"[split_db] ✓ Checksum OK: {actual}")
    else:
        print(f"[split_db] ✓ Ghép xong (không có file .md5 để verify).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reassemble", action="store_true",
                        help="Ghép các part lại thành chroma.sqlite3")
    args = parser.parse_args()

    if args.reassemble:
        reassemble()
    else:
        split()
