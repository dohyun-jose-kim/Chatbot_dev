"""ChromaDB Retriever

Loads the ChromaDB collection and PubMedBERT model.
Embeds a query string and returns the top-K most similar papers.
"""
import sys
from pathlib import Path

# ── Config import ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel

from config import (
    CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, EMBED_MAX_LENGTH, TOP_K,
)


def mean_pooling(model_output, attention_mask):
    """Attention-aware mean pooling — identical to embed.py for vector space consistency."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    summed = torch.sum(token_embeddings * mask_expanded, dim=1)
    counted = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return summed / counted


class Retriever:
    def __init__(self):
        # ChromaDB
        chroma_path = str(CHROMA_DIR)
        if not Path(chroma_path).exists():
            raise FileNotFoundError(
                f"ChromaDB not found at {chroma_path}. Run build_db.py first."
            )
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_collection(name=COLLECTION_NAME)

        # PubMedBERT for query embedding
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
        self.model = AutoModel.from_pretrained(EMBED_MODEL)
        self.model.eval()
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = self.model.to(self.device)

        print(f"Retriever ready (device: {self.device}, docs: {self.collection.count():,})")

    def _embed_query(self, text):
        """Embed a single query string to a 768-dim vector."""
        encoded = self.tokenizer(
            [text], padding=True, truncation=True,
            max_length=EMBED_MAX_LENGTH, return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output = self.model(**encoded)

        embedding = mean_pooling(output, encoded["attention_mask"])
        return embedding.squeeze().cpu().numpy().tolist()

    def search(self, query, top_k=TOP_K):
        """Search for the top-K most similar papers to the query."""
        query_embedding = self._embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        papers = []
        for i in range(len(results["ids"][0])):
            papers.append({
                "pmid": results["ids"][0][i],
                "abstract": results["documents"][0][i],
                "title": results["metadatas"][0][i].get("title", ""),
                "year": results["metadatas"][0][i].get("year", 0),
                "journal": results["metadatas"][0][i].get("journal", ""),
                "mesh_terms": results["metadatas"][0][i].get("mesh_terms", ""),
                "distance": results["distances"][0][i],
            })

        return papers
