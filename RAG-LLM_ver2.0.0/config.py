"""Central Configuration

PubMed 코퍼스(5,590편)의 PubMedBERT 임베딩이 적재된 chroma_db를 조회한다.
DB는 이 프로젝트에 함께 동봉되어 있다(chroma_db/). DB 빌드 파이프라인(수집→전처리→
스크리닝→임베딩→적재)의 코드는 전신 버전(태그 v1.0.0)에 보존되어 있다.
"""
import os
from pathlib import Path

# ── 동봉 chroma_db ──
PROJECT_DIR = Path(__file__).resolve().parent
CHROMA_DIR = str(PROJECT_DIR / "chroma_db")
COLLECTION_NAME = "pubmed_abstracts"

# ── Embedding Model (PubMedBERT) — ver1과 동일해야 벡터공간 일치 ──
EMBED_MODEL = "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext"
EMBED_MAX_LENGTH = 512

# ── Retrieval ──
TOP_K = 5

# ── LLM (Ollama) ──
LLM_MODEL = "gemma4:31b"   # 품질 확인용
DEV_MODEL = "gemma4:26b"   # 개발/디버깅용 (tool-calling 지원; gemma3:4b는 tool 미지원)

# ── Live PubMed (Entrez) — search_pubmed_live tool ──
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "your_email@example.com")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")

# ── Agent system prompt (ver2.6.0: 라우팅 + 인용) ──
AGENT_SYSTEM_PROMPT = """You are a research assistant specializing in fishery byproduct bioactivity.

You have two search tools:
- search_local_corpus: a curated local corpus of 5,590 PubMed abstracts on fishery-byproduct
  bioactivity. Try this FIRST for domain questions.
- search_pubmed_live: live search over the entire PubMed database. Use when the local corpus
  lacks relevant information, or when the user asks for the latest or broader literature.

Rules:
- Use the tools to gather evidence before answering; do not answer from prior knowledge alone.
- Cite every claim with the paper's PMID, e.g. (PMID: 12345678).
- If the tools return no relevant information, say so explicitly.
"""

# ── Prompts ──
SYSTEM_PROMPT = """\
You are a research assistant specializing in fishery byproduct bioactivity.

Rules:
- Answer based ONLY on the provided PubMed abstracts.
- Cite every claim with the paper's PMID, e.g. (PMID: 12345678).
- If the provided papers do not contain relevant information, say so explicitly.
- Structure your answer: (1) Key findings, (2) Supporting details per paper, (3) Cited paper list.
"""

# create_stuff_documents_chain의 document_prompt로 주입할 논문 포맷
CONTEXT_TEMPLATE = """\
[Paper] PMID: {pmid} | {year} | {journal}
Title: {title}
Abstract: {page_content}"""
