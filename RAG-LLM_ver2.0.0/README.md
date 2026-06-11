# Fishery Byproduct Bioactivity — 대화형 RAG 챗봇

수산부산물 기능성 PubMed 논문 **5,590편**을 근거로, 멀티턴 대화를 유지하며 **PMID를 인용해**
답변하는 Retrieval-Augmented Generation 챗봇.

- **검색**: PubMedBERT 쿼리 임베딩 → ChromaDB(코사인/ L2) 유사도 검색 (DB 동봉)
- **대화**: LangChain history-aware retriever로 후속 질문의 대명사·생략을 해소
- **생성**: 로컬 **Ollama**(gemma) — API 키·비용·외부 전송 없음
- **인터페이스**: FastAPI 백엔드(:8000) + Streamlit 프론트(:8501), CLI도 제공

> 전신 버전 **v1.0.0**("Domain RAG Search Engine", stateless 단일턴 Q&A + 데이터 수집~DB
> 구축 풀 파이프라인)은 git **태그 `v1.0.0`** 에 보존되어 있다. 본 프로젝트는 그 chroma_db를
> 동봉해 **대화형 RAG**로 확장한 후속 버전이며, 독립적으로 동작한다.

현재 버전: **2.2.0** (FastAPI + Streamlit 통합).

---

## 기술 스택

| 구성요소 | 기술 |
|---|---|
| Embedding (쿼리) | PubMedBERT (`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`) |
| Vector DB | ChromaDB (`PersistentClient`, 동봉된 `chroma_db/`) |
| RAG 프레임워크 | LangChain (`create_history_aware_retriever` + `create_retrieval_chain`) |
| LLM | Ollama — `gemma4:31b`(품질) / `gemma3:4b`(개발) |
| 대화 기억 | SQLite (세션별 `application_logs`) |
| Backend / Frontend | FastAPI / Streamlit |

---

## 아키텍처

```
브라우저 ── Streamlit(06_ui, :8501) ──HTTP POST /chat──> FastAPI(05_api, :8000)
                                                              │
                                  get_rag_chain(02) + db_utils(03) + retriever(01)
                                                              │
                                                   동봉 chroma_db/ (PubMed 5,590편)
```

런타임 흐름이 폴더 번호대로 흐른다: `01 검색 → 02 체인 → 03 기억 → 04 대화`,
그리고 이를 서비스로 노출하는 `05 API → 06 UI`. CLI(`04_interface/chat.py`)는
API 없이 같은 체인을 직접 호출한다.

---

## 디렉터리 구조

```
RAG-LLM_ver2.0.0/
├── config.py                    # 공유 설정: chroma_db 경로, 모델명, TOP_K, 프롬프트
├── requirements.txt
├── run_app.sh                   # FastAPI(:8000) + Streamlit(:8501) 동시 기동
├── chroma_db/                   # 동봉 벡터 DB (PubMed 5,590편, PubMedBERT 임베딩)
├── 00_Docs/
│   ├── FastAPI+Streamlit.md     # 2-tier 구조 학습 노트
│   └── version_management/      # 버전별 PLAN/VERIFY 문서
├── 01_retrieval/
│   └── pubmedbert_retriever.py  # PubMedBERT 쿼리 임베딩 → chroma 검색 (LangChain BaseRetriever)
├── 02_chain/
│   └── rag_chain.py             # 멀티턴 체인: ChatOllama + history-aware retriever
├── 03_memory/
│   └── db_utils.py              # 세션별 대화기록 SQLite (chat_history.db는 gitignore)
├── 04_interface/
│   └── chat.py                  # CLI 멀티턴 루프
├── 05_api/
│   ├── main.py                  # FastAPI: POST /chat (체인 모델별 캐시)
│   └── models.py                # pydantic QueryInput / QueryResponse
└── 06_ui/
    ├── streamlit_app.py         # 진입점, session_state 초기화
    ├── chat_interface.py        # 말풍선 + 검색 PMID expander
    ├── api_utils.py             # /chat HTTP 클라이언트
    └── sidebar.py               # 모델 선택 + 새 세션
```

---

## 셋업

```bash
# 1. 의존성 (저장소 루트의 .venv 재사용)
../.venv/bin/python -m pip install -r requirements.txt
#  (또는 로컬 venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)

# 2. Ollama 모델 (로컬에서 실행 중이어야 함)
ollama list          # gemma4:31b(품질) / gemma3:4b(개발) 확인
```

PubMedBERT는 첫 실행 시 HuggingFace에서 자동 다운로드된다(~500MB). chroma_db는 동봉되어
있어 별도 빌드가 필요 없다.

---

## 실행

```bash
# 웹 (FastAPI + Streamlit 동시 기동)
./run_app.sh                     # → http://localhost:8501

# CLI
../.venv/bin/python 04_interface/chat.py          # 품질 모델 (gemma4:31b)
../.venv/bin/python 04_interface/chat.py --dev    # 개발 모델 (gemma3:4b, 빠름)
```

`NN_` 폴더는 숫자로 시작해 Python `import`가 안 되므로, 진입점(`chat.py`/`main.py`)에서만
각 스테이지를 `sys.path`에 등록한다.

---

## 멀티턴 동작 (검증 시나리오)

```
Q1: "What bioactivities does fish scale collagen have?"
Q2: "What about its antioxidant effects?"   ← 대명사 "its"
```

Q2는 대화기록과 합쳐져 standalone 질문으로 재작성된 뒤 검색되고, 답변은 PMID 인용 형식을
유지한다. 모델별 관찰은 [`00_Docs/version_management/ver2.0.1_+Multi-turn+LangChain/VERIFY.md`]
참고(`gemma4:31b`이 근거 없는 주장을 더 정직하게 거른다. 후속 턴 ≈ 60~70초).

---

## 버전 로드맵

| 버전 | 내용 | 상태 |
|---|---|---|
| 2.0.1 | Multi-turn + LangChain + Ollama 전환 | ✅ 완료 (tag `v2.0.1`) |
| 2.2.0 | API + UI (FastAPI + Streamlit) | ✅ 완료 (tag `v2.2.0`) |
| 2.4.0 | user config, id/pw | 예정 |
| 2.5.0 | server deploy | 예정 |
| 2.6.0 | LangGraph 에이전트화 — RAG를 tool로 편입, 멀티 tool 오케스트레이션 | 예정 |

품질 평가(RAGAS), 검색 고도화(re-ranking, hybrid, 코사인 전환), 응답 스트리밍은 향후 과제.
