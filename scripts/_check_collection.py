"""
_check_collection.py — Helper nội bộ, dùng bởi build_db.cmd / build_all_variants.cmd
In ra số vectors của collection ra stdout. In -1 nếu collection chưa tồn tại.

Cách dùng:
    python scripts\_check_collection.py <embed> <variant> <strategy>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import chromadb
from config import build_collection_name, CHROMA_DIR

embed    = sys.argv[1] if len(sys.argv) > 1 else ""
variant  = sys.argv[2] if len(sys.argv) > 2 else ""
strategy = sys.argv[3] if len(sys.argv) > 3 else ""

if not embed or not variant or not strategy:
    print(-1)
    sys.exit(0)

try:
    name   = build_collection_name(embed, variant, strategy)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    cols   = [c.name for c in client.list_collections()]
    if name in cols:
        print(client.get_collection(name).count())
    else:
        print(-1)
except Exception:
    print(-1)
