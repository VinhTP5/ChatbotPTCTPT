#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

scripts/build_db.sh coarse standard minilm
scripts/build_db.sh balanced standard mpnet
scripts/build_db.sh fine standard mpnet
scripts/build_db.sh balanced late mpnet
scripts/build_db.sh balanced long_late bge_m3
scripts/build_db.sh fine long_late bge_m3

python src/build_db.py --mode status
