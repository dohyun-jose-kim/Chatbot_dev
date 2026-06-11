"""PubMedBERT Retriever — LangChain BaseRetriever 어댑터

ver1 03_chatbot/retriever.py의 검색 로직(mean_pooling + 쿼리 임베딩 + chroma 검색)을
복사해와 LangChain BaseRetriever로 감싼다. ver1은 PMID를 chroma의 id로 저장하므로
검색 결과를 Document(metadata={pmid, ...})로 변환해 PMID 인용이 깨지지 않게 한다.
"""
from typing import List

import chromadb
import torch
from transformers import AutoTokenizer, AutoModel
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import PrivateAttr

from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, EMBED_MAX_LENGTH, TOP_K


def mean_pooling(model_output, attention_mask):
    """Attention-aware mean pooling — ver1 embed.py와 동일해야 벡터공간이 일치한다."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    summed = torch.sum(token_embeddings * mask_expanded, dim=1)
    counted = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return summed / counted


class PubMedBERTRetriever(BaseRetriever):
    """ver1 chroma_db를 PubMedBERT로 쿼리 임베딩해 검색하는 LangChain retriever."""

    k: int = TOP_K

    _collection = PrivateAttr()
    _tokenizer = PrivateAttr()
    _model = PrivateAttr()
    _device = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self._collection = client.get_collection(name=COLLECTION_NAME)

        self._tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
        self._model = AutoModel.from_pretrained(EMBED_MODEL)
        self._model.eval()
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._model = self._model.to(self._device)

    def _embed_query(self, text: str) -> List[float]:
        encoded = self._tokenizer(
            [text], padding=True, truncation=True,
            max_length=EMBED_MAX_LENGTH, return_tensors="pt",
        ).to(self._device)
        with torch.no_grad():
            output = self._model(**encoded)
        embedding = mean_pooling(output, encoded["attention_mask"])
        return embedding.squeeze().cpu().numpy().tolist()

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        results = self._collection.query(
            query_embeddings=[self._embed_query(query)],
            n_results=self.k,
            include=["documents", "metadatas", "distances"],
        )
        docs = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            docs.append(Document(
                page_content=results["documents"][0][i],
                metadata={
                    "pmid": results["ids"][0][i],
                    "title": meta.get("title", ""),
                    "year": meta.get("year", 0),
                    "journal": meta.get("journal", ""),
                    "distance": results["distances"][0][i],
                },
            ))
        return docs
