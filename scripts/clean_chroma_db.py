import os
import sys
from pathlib import Path
import chromadb

# Ensure src is in python path
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import CHROMA_DIR

def main():
    print("=" * 72)
    print("   CLEAN CHROMA DB - Obsolete & Corrupted Collections Cleanup")
    print("=" * 72)
    print(f"Connecting to ChromaDB at: {CHROMA_DIR}")
    
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        return

    try:
        collections = client.list_collections()
    except Exception as e:
        print(f"Error listing collections: {e}")
        return

    print(f"Found {len(collections)} collections in database.")
    
    # We only keep collections that start with minilm__ or bge_m3__
    kept_embeds = {"minilm", "bge_m3"}
    
    deleted_count = 0
    kept_count = 0
    for col in collections:
        name = col.name
        # Parse embed alias
        parts = name.split("__")
        is_allowed = len(parts) == 3 and parts[0] in kept_embeds
        
        # Check if it's healthy
        is_healthy = True
        try:
            col_obj = client.get_collection(name)
            count = col_obj.count()
            print(f"  - {name}: healthy ({count} vectors)")
        except Exception as e:
            print(f"  - {name}: CORRUPTED/UNHEALTHY ({e})")
            is_healthy = False
            
        if not is_allowed or not is_healthy:
            reason = "unsupported embedding" if not is_allowed else "corrupted/unhealthy"
            print(f"    -> Deleting collection '{name}' ({reason})...")
            try:
                client.delete_collection(name)
                print(f"    [OK] Deleted collection '{name}'")
                deleted_count += 1
            except Exception as e:
                print(f"    [ERR] Error deleting collection '{name}': {e}")
        else:
            kept_count += 1
                
    print(f"\nSummary of collections:")
    print(f"  Kept: {kept_count}")
    print(f"  Deleted: {deleted_count}")
    
    # Clean up registry files in chroma_db/
    print("\nCleaning up registry files in chroma_db/...")
    db_path = Path(CHROMA_DIR)
    if db_path.exists():
        json_files = list(db_path.glob("indexed_files__*.json"))
        deleted_files = 0
        kept_files = 0
        for f in json_files:
            name = f.name
            # Format: indexed_files__<embed_alias>__<variant>__<strategy>.json
            parts = name.replace("indexed_files__", "").replace(".json", "").split("__")
            is_allowed = len(parts) == 3 and parts[0] in kept_embeds
            if not is_allowed:
                print(f"  - Deleting obsolete registry: {f.name}")
                try:
                    f.unlink()
                    deleted_files += 1
                except Exception as e:
                    print(f"  - [ERR] Error deleting {f.name}: {e}")
            else:
                kept_files += 1
        print(f"Summary of registry files:")
        print(f"  Kept: {kept_files}")
        print(f"  Deleted: {deleted_files}")
    print("=" * 72)

if __name__ == "__main__":
    main()
