"""RAG Pipeline — Central Configuration

All paths, model names, hyperparameters, and prompts are defined here.
Every script in the pipeline imports from this module.
"""
from pathlib import Path

# ── Paths ──
PIPELINE_DIR = Path(__file__).resolve().parent
DATA_DIR = PIPELINE_DIR / "data"
OUTPUT_DIR = PIPELINE_DIR / "outputs"

# outputs/01_embedding/
EMBED_OUTPUT_DIR = OUTPUT_DIR / "01_embedding"
EMBEDDINGS_NPY = EMBED_OUTPUT_DIR / "embeddings.npy"
PMIDS_CSV = EMBED_OUTPUT_DIR / "pmids.csv"
EMBED_CHECKPOINT_DIR = EMBED_OUTPUT_DIR / "checkpoints"

# outputs/02_vectordb/
VECTORDB_OUTPUT_DIR = OUTPUT_DIR / "02_vectordb"
CHROMA_DIR = VECTORDB_OUTPUT_DIR / "chroma_db"

# outputs/logs/
LOG_DIR = OUTPUT_DIR / "logs"
EMBED_LOG = LOG_DIR / "embed_log.txt"

SCREENED_CSV = DATA_DIR / "screened.csv"

# ── CSV Column Names ──
# screened.csv has 11 columns (BOM-prefixed but pandas handles it):
#   pmid, title, abstract, authors, journal, year,
#   mesh_terms, abstract_clean, kw_part, kw_category, kw_fn
COL_PMID = "pmid"
COL_TITLE = "title"
COL_ABSTRACT = "abstract"
COL_AUTHORS = "authors"
COL_JOURNAL = "journal"
COL_YEAR = "year"
COL_MESH = "mesh_terms"

# ── Embedding Model (PubMedBERT) ──
EMBED_MODEL = "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext"
EMBED_BATCH_SIZE = 32
EMBED_MAX_LENGTH = 512
EMBED_DIM = 768

# ── VectorDB (ChromaDB) ──
COLLECTION_NAME = "pubmed_abstracts"
CHROMA_BATCH_SIZE = 500

# ── LLM ──
# Backend: "claude" or "gemini"
LLM_BACKEND = "claude"

# Claude
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 1024

# Gemini (free tier: 15 RPM)
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_MAX_TOKENS = 1024

# ── Retrieval ──
TOP_K = 5

# ── Prompts ──
SYSTEM_PROMPT = """\
You are a research assistant specializing in fishery byproduct bioactivity.

Rules:
- Answer based ONLY on the provided PubMed abstracts.
- Cite every claim with the paper's PMID, e.g. (PMID: 12345678).
- If the provided papers do not contain relevant information, say so explicitly.
- Structure your answer: (1) Key findings, (2) Supporting details per paper, (3) Cited paper list.
"""

USER_PROMPT_TEMPLATE = """\
Below are PubMed abstracts relevant to the question.

{context}

---
Question: {question}
"""

CONTEXT_TEMPLATE = """\
[Paper {i}] PMID: {pmid} | {year} | {journal}
Title: {title}
Abstract: {abstract}
"""
