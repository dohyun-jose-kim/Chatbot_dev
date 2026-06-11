# Chatbot-RAG-LLM

수산부산물 기능성 PubMed 논문(5,590편)을 근거로 PMID를 인용해 답하는 **대화형 RAG 챗봇**.
PubMedBERT 검색 + ChromaDB + LangChain + 로컬 Ollama, FastAPI/Streamlit 인터페이스.

본체는 [`RAG-LLM_ver2.0.0/`](RAG-LLM_ver2.0.0/) 에 있으며 독립적으로 동작한다 — 셋업·실행·구조는
해당 폴더의 [README](RAG-LLM_ver2.0.0/README.md) 참고.

## 버전

- **v2.x** (현행): 멀티턴 대화형 RAG. `RAG-LLM_ver2.0.0/`.
- **v1.0.0** (보존): 단일턴 Q&A + 데이터 수집~DB구축 풀 파이프라인("Domain RAG Search Engine").
  git 태그 **`v1.0.0`** 로 보존 — `git checkout v1.0.0` 으로 열람 가능.
