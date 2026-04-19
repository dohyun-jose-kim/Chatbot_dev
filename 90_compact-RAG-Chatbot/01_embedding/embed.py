"""PubMedBERT Embedding Generator

Reads screened.csv abstracts, generates 768-dim embeddings via PubMedBERT,
and saves to embeddings.npy + pmids.csv.

Includes checkpoint logic: saves every 50 batches so a crash doesn't
lose all progress. On restart, resumes from the last checkpoint.

Usage:
    python 01_embedding/embed.py                        # full dataset
    python 01_embedding/embed.py data/screened_1of3.csv  # shard
"""
import sys
import time
import argparse
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

# ── Config import ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    SCREENED_CSV, EMBED_OUTPUT_DIR, EMBEDDINGS_NPY, PMIDS_CSV,
    EMBED_CHECKPOINT_DIR, EMBED_MODEL, EMBED_BATCH_SIZE,
    EMBED_MAX_LENGTH, COL_PMID, COL_ABSTRACT, PIPELINE_DIR,
)

CHECKPOINT_INTERVAL = 50  # save every N batches


def load_model():
    """Load PubMedBERT tokenizer and model."""
    print(f"Loading model: {EMBED_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
    model = AutoModel.from_pretrained(EMBED_MODEL)
    model.eval()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = model.to(device)
    print(f"  Device: {device}")
    return tokenizer, model, device


def mean_pooling(model_output, attention_mask):
    """Attention-aware mean pooling of token embeddings."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    summed = torch.sum(token_embeddings * mask_expanded, dim=1)
    counted = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return summed / counted


def load_checkpoint(ckpt_dir):
    """Load the latest checkpoint if it exists. Returns (embeddings_list, start_batch_idx)."""
    if not ckpt_dir.exists():
        return [], 0

    chunks = sorted(ckpt_dir.glob("chunk_*.npy"))
    if not chunks:
        return [], 0

    embeddings = []
    for chunk_path in chunks:
        embeddings.append(np.load(chunk_path))
        print(f"  Loaded checkpoint: {chunk_path.name} ({embeddings[-1].shape[0]} rows)")

    total_rows = sum(e.shape[0] for e in embeddings)
    start_batch = total_rows // EMBED_BATCH_SIZE
    print(f"  Resuming from batch {start_batch} ({total_rows} rows already done)")
    return embeddings, start_batch


def save_checkpoint(ckpt_dir, embeddings_chunk, chunk_idx):
    """Save an embedding chunk to disk."""
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = ckpt_dir / f"chunk_{chunk_idx:04d}.npy"
    np.save(path, embeddings_chunk)


def embed_texts(texts, tokenizer, model, device, ckpt_dir, start_batch=0):
    """Embed texts in batches with checkpoint support. Returns list of numpy arrays."""
    all_chunks = []
    current_chunk = []
    total_batches = (len(texts) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    chunk_idx = start_batch // CHECKPOINT_INTERVAL
    t_start = time.time()

    for batch_idx in range(start_batch, total_batches):
        i = batch_idx * EMBED_BATCH_SIZE
        batch = texts[i : i + EMBED_BATCH_SIZE]

        encoded = tokenizer(
            batch, padding=True, truncation=True,
            max_length=EMBED_MAX_LENGTH, return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            output = model(**encoded)

        embeddings = mean_pooling(output, encoded["attention_mask"])
        current_chunk.append(embeddings.cpu().numpy())

        # Progress + ETA
        done = batch_idx + 1
        elapsed = time.time() - t_start
        if done > start_batch:
            batches_done = done - start_batch
            eta = elapsed / batches_done * (total_batches - done)
            eta_str = f"{eta / 60:.1f}min"
        else:
            eta_str = "..."
        print(f"  Batch {done}/{total_batches} | ETA: {eta_str}", end="\r")

        # Checkpoint
        if (done - start_batch) % CHECKPOINT_INTERVAL == 0:
            chunk_arr = np.vstack(current_chunk)
            save_checkpoint(ckpt_dir, chunk_arr, chunk_idx)
            all_chunks.append(chunk_arr)
            current_chunk = []
            chunk_idx += 1

    # Save remaining
    if current_chunk:
        chunk_arr = np.vstack(current_chunk)
        save_checkpoint(ckpt_dir, chunk_arr, chunk_idx)
        all_chunks.append(chunk_arr)

    print()
    return all_chunks


def parse_args():
    parser = argparse.ArgumentParser(description="PubMedBERT Embedding Generator")
    parser.add_argument("input_csv", nargs="?", default=None,
                        help="Input CSV path relative to RAG_Pipeline/ (default: full screened.csv)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve input/output paths
    if args.input_csv:
        input_csv = (PIPELINE_DIR / args.input_csv).resolve()
        stem = input_csv.stem.replace("screened", "")  # e.g. "_1of3"
        out_npy = EMBED_OUTPUT_DIR / f"embeddings{stem}.npy"
        out_pmids = EMBED_OUTPUT_DIR / f"pmids{stem}.csv"
        ckpt_dir = EMBED_OUTPUT_DIR / f"checkpoints{stem}"
    else:
        input_csv = SCREENED_CSV
        out_npy = EMBEDDINGS_NPY
        out_pmids = PMIDS_CSV
        ckpt_dir = EMBED_CHECKPOINT_DIR

    print("=" * 60)
    print("PubMedBERT Embedding Generator")
    print("=" * 60)
    print(f"Input:  {input_csv}")
    print(f"Output: {out_npy}")

    # Load data
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    print(f"\nTotal papers: {len(df):,}")

    df = df.dropna(subset=[COL_ABSTRACT])
    df = df[df[COL_ABSTRACT].str.strip().astype(bool)].reset_index(drop=True)
    print(f"Valid abstracts: {len(df):,}")

    texts = df[COL_ABSTRACT].tolist()

    # Check for existing checkpoint
    checkpoint_chunks, start_batch = load_checkpoint(ckpt_dir)

    # Load model
    tokenizer, model, device = load_model()

    # Embed
    t0 = time.time()
    new_chunks = embed_texts(texts, tokenizer, model, device, ckpt_dir, start_batch)
    elapsed = time.time() - t0

    # Merge all chunks
    all_chunks = checkpoint_chunks + new_chunks
    embeddings = np.vstack(all_chunks)
    print(f"\nEmbedding shape: {embeddings.shape}")
    print(f"Time: {elapsed / 60:.1f} min")

    # Save final output
    EMBED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(out_npy, embeddings)
    print(f"Saved: {out_npy}")

    df[[COL_PMID]].to_csv(out_pmids, index=False)
    print(f"Saved: {out_pmids}")

    # Cleanup checkpoints
    if ckpt_dir.exists():
        for f in ckpt_dir.glob("chunk_*.npy"):
            f.unlink()
        ckpt_dir.rmdir()
        print("Checkpoints cleaned up.")

    print("\nDone!")


if __name__ == "__main__":
    main()
