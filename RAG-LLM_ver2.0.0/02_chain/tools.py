"""Agent tools (ver2.6.0)

두 검색 tool을 LangChain `@tool`로 노출한다:
- search_local_corpus : 동봉 chroma 코퍼스(PubMedBERTRetriever) 조회 — 본분(RAG)
- search_pubmed_live  : Entrez로 PubMed 전체 라이브 검색 (ver1 collect_pubmed.py 차용)

무거운 retriever(PubMedBERT)는 import 시가 아니라 첫 tool 호출 시 1회만 로드(lru_cache).
"""
import xml.etree.ElementTree as ET
from functools import lru_cache

import requests
from langchain_core.tools import tool

from config import NCBI_EMAIL, NCBI_API_KEY

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


@lru_cache(maxsize=1)
def _retriever():
    """PubMedBERTRetriever를 1회 로드(요청마다 재로드 방지). 01_retrieval이 sys.path에 있어야 함."""
    from pubmedbert_retriever import PubMedBERTRetriever
    return PubMedBERTRetriever()


@tool
def search_local_corpus(query: str) -> str:
    """Search the curated local corpus of 5,590 PubMed abstracts on fishery-byproduct
    bioactivity. Returns the most relevant papers with PMID, year, journal, title, abstract."""
    docs = _retriever().invoke(query)
    if not docs:
        return "No relevant papers found in the local corpus."
    parts = []
    for d in docs:
        m = d.metadata
        parts.append(
            f"[PMID: {m.get('pmid', '')}] {m.get('year', '')} | {m.get('journal', '')}\n"
            f"Title: {m.get('title', '')}\n"
            f"Abstract: {d.page_content[:1500]}"
        )
    return "\n\n".join(parts)


@tool
def search_pubmed_live(query: str) -> str:
    """Search PubMed live across the entire database (beyond the local corpus) for recent or
    broader literature. Use when the local corpus lacks relevant papers or the user wants the
    latest findings. Returns up to 5 papers with PMID, title, abstract."""
    params = {"db": "pubmed", "term": query, "retmax": 5, "retmode": "json", "email": NCBI_EMAIL}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        r = requests.get(ESEARCH_URL, params=params, timeout=15)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        return f"PubMed live search failed (esearch): {e}"
    if not ids:
        return "No papers found on PubMed for this query."

    fparams = {"db": "pubmed", "id": ",".join(ids), "rettype": "abstract",
               "retmode": "xml", "email": NCBI_EMAIL}
    if NCBI_API_KEY:
        fparams["api_key"] = NCBI_API_KEY
    try:
        r = requests.get(EFETCH_URL, params=fparams, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        return f"PubMed live search failed (efetch): {e}"

    parts = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID", "")
        title = art.findtext(".//Article/ArticleTitle", "")
        abstract = " ".join("".join(at.itertext())
                            for at in art.findall(".//Abstract/AbstractText"))
        parts.append(f"[PMID: {pmid}] (PubMed live)\nTitle: {title}\nAbstract: {abstract[:1200]}")
    return "\n\n".join(parts) if parts else "No abstracts retrieved from PubMed."
