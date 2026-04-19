"""ChromaDB Builder

Loads PubMedBERT embeddings + metadata from screened.csv,
stores them in a ChromaDB persistent collection.
Runs a built-in verification query after building.

Usage:
    python 02_vectordb/build_db.py
"""
import sys
import numpy as np
import pandas as pd
import chromadb
from pathlib import Path

# ── Config import ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    SCREENED_CSV, EMBEDDINGS_NPY, PMIDS_CSV, CHROMA_DIR, VECTORDB_OUTPUT_DIR,
    COLLECTION_NAME, CHROMA_BATCH_SIZE,
    COL_PMID, COL_TITLE, COL_ABSTRACT, COL_YEAR, COL_JOURNAL, COL_MESH,
)


def load_data():
    """Load screened CSV, embeddings, and PMID mapping."""
    df = pd.read_csv(SCREENED_CSV, encoding="utf-8-sig")
    embeddings = np.load(EMBEDDINGS_NPY)
    pmids_df = pd.read_csv(PMIDS_CSV)

    assert len(pmids_df) == embeddings.shape[0], (
        f"PMID count ({len(pmids_df)}) != embedding count ({embeddings.shape[0]})"
    )

    # Filter to papers with embeddings
    pmid_set = set(pmids_df[COL_PMID].astype(str))
    df["pmid_str"] = df[COL_PMID].astype(str)
    df = df[df["pmid_str"].isin(pmid_set)].reset_index(drop=True)

    return df, embeddings, pmids_df


def build_db(df, embeddings):
    """Build ChromaDB collection from dataframe and embeddings."""
    VECTORDB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Drop existing collection if present
    try:
        client.delete_collection(COLLECTION_NAME)
        print("  Deleted existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "PubMed fishery byproduct abstracts with PubMedBERT embeddings"},
    )

    total = len(df)
    for start in range(0, total, CHROMA_BATCH_SIZE):
        end = min(start + CHROMA_BATCH_SIZE, total)
        batch_df = df.iloc[start:end]
        batch_emb = embeddings[start:end]

        ids = batch_df[COL_PMID].astype(str).tolist()
        documents = batch_df[COL_ABSTRACT].fillna("").tolist()
        emb_list = batch_emb.tolist()

        metadatas = []
        for _, row in batch_df.iterrows():
            meta = {
                "pmid": str(row.get(COL_PMID, "")),
                "title": str(row.get(COL_TITLE, ""))[:500],
                "year": int(row[COL_YEAR]) if pd.notna(row.get(COL_YEAR)) else 0,
                "journal": str(row.get(COL_JOURNAL, ""))[:200],
                "mesh_terms": str(row.get(COL_MESH, ""))[:500],
            }
            metadatas.append(meta)

        collection.add(
            ids=ids,
            embeddings=emb_list,
            documents=documents,
            metadatas=metadatas,
        )
        print(f"  Stored: {end:,} / {total:,}", end="\r")

    print(f"\n  Total: {collection.count():,} documents")
    return client, collection


def test_query(collection):
    """Verify DB with a simple similarity search using the first document."""
    print("\n-- Verification Query --")

    first = collection.get(limit=1, include=["embeddings"])
    print(f"  Query: nearest neighbors of PMID={first['ids'][0]}")

    results = collection.query(
        query_embeddings=first["embeddings"],
        n_results=5,
    )

    for i, (doc_id, meta, dist) in enumerate(
        zip(results["ids"][0], results["metadatas"][0], results["distances"][0])
    ):
        print(f"  [{i+1}] PMID: {doc_id} (dist: {dist:.4f})")
        print(f"      {meta.get('title', '')[:80]}")

    print("\nVerification passed.")


def main():
    print("=" * 60)
    print("ChromaDB Builder")
    print("=" * 60)

    print("\nLoading data...")
    df, embeddings, pmids_df = load_data()
    print(f"  Papers: {len(df):,}")
    print(f"  Embeddings: {embeddings.shape}")

    print("\nBuilding ChromaDB...")
    client, collection = build_db(df, embeddings)
    print(f"  Path: {CHROMA_DIR}")

    test_query(collection)
    print("\nDone!")


if __name__ == "__main__":
    main()
