"""ver2.0.1 — Central Configuration

ver1(90_RAG-Pipeline)의 chroma_db를 읽기 전용으로 참조한다.
ver1 파일은 import하지 않고, 필요한 값만 여기에 복사/명시한다.
"""
from pathlib import Path

# ── ver1 chroma_db (읽기 전용 참조) ──
VER1_DIR = Path("/Users/inco/01_Projects/dohyun-jose-kim/03_Chatbot-RAG-LLM/90_RAG-Pipeline")
CHROMA_DIR = str(VER1_DIR / "outputs" / "02_vectordb" / "chroma_db")
COLLECTION_NAME = "pubmed_abstracts"

# ── Embedding Model (PubMedBERT) — ver1과 동일해야 벡터공간 일치 ──
EMBED_MODEL = "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext"
EMBED_MAX_LENGTH = 512

# ── Retrieval ──
TOP_K = 5

# ── LLM (Ollama) ──
LLM_MODEL = "gemma4:31b"   # 품질 확인용
DEV_MODEL = "gemma3:4b"    # 개발/디버깅용 (멀티턴은 턴당 LLM 2회 호출)

# ── Prompts (ver1 config.py에서 차용) ──
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
