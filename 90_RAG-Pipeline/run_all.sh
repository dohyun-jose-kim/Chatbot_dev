#!/bin/bash
# RAG Pipeline — Full execution script
# Usage: cd RAG_Pipeline && bash run_all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Use activated venv's python, or fallback to system python
VENV="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}"
VENV="${VENV:-python3}"

# Load API keys
source ~/.anthropic_key 2>/dev/null || true
source ~/.zshrc 2>/dev/null || true
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
export TOKENIZERS_PARALLELISM=false

echo "============================================================"
echo "RAG Pipeline — Full Execution"
echo "============================================================"
echo "Working directory: $SCRIPT_DIR"
echo ""

# Step 1: Embedding
echo "=== Step 1/3: Generating PubMedBERT embeddings ==="
if [ -f "$SCRIPT_DIR/outputs/01_embedding/embeddings.npy" ]; then
    echo "  embeddings.npy already exists — skipping."
    echo "  (delete outputs/01_embedding/embeddings.npy to re-run)"
else
    $VENV "$SCRIPT_DIR/01_embedding/embed.py"
fi
echo ""

# Step 2: Build ChromaDB
echo "=== Step 2/3: Building ChromaDB ==="
if [ -d "$SCRIPT_DIR/outputs/02_vectordb/chroma_db" ]; then
    echo "  chroma_db/ already exists — rebuilding."
fi
$VENV "$SCRIPT_DIR/02_vectordb/build_db.py"
echo ""

# Step 3: Launch chatbot with auto-logging
# Log format: YYYYMMDD_NN.md (auto-incrementing sequence per date)
LOG_DIR="$SCRIPT_DIR/Docs/logs"
mkdir -p "$LOG_DIR"

TODAY=$(date +%Y%m%d)
SEQ=1
while [ -f "$LOG_DIR/${TODAY}_$(printf '%02d' $SEQ).md" ]; do
    SEQ=$((SEQ + 1))
done
LOG_FILE="$LOG_DIR/${TODAY}_$(printf '%02d' $SEQ).md"

echo "=== Step 3/3: Launching Chatbot ==="
echo "Log: $LOG_FILE"
echo "(Ctrl+C or type 'quit' to exit)"
echo ""
$VENV "$SCRIPT_DIR/03_chatbot/chatbot.py" 2>&1 | tee "$LOG_FILE"
