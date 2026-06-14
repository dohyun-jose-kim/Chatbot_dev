# Fishery Byproduct Bioactivity — Agentic RAG 챗봇

수산부산물 기능성 PubMed 논문 **5,590편**을 근거로, 멀티턴 대화를 유지하며 **PMID를 인용해**
답하는 tool-calling 에이전트. 동봉 코퍼스를 먼저 찾고, 부족하면 PubMed를 라이브로 검색한다.

- **에이전트**: LangGraph tool-calling 에이전트(`langchain.agents.create_agent`)가 2개 검색 tool을 오케스트레이션
  - `search_local_corpus` — 동봉 코퍼스(PubMedBERT 임베딩 + ChromaDB) 조회 (본분)
  - `search_pubmed_live` — Entrez로 PubMed 전체 라이브 검색 (코퍼스 밖 최신·광범위 문헌)
- **대화**: 후속 질문의 대명사·생략을 에이전트가 대화기록(`SqliteSaver` 체크포인터)으로 해소
- **생성**: 로컬 **Ollama**(gemma4) — API 키·비용·외부 전송 없음
- **인터페이스**: FastAPI 백엔드(:8000) + Streamlit 프론트(:8501, tool 호출 노출), CLI도 제공

> 전신 버전 **v1.0.0**("Domain RAG Search Engine", stateless 단일턴 Q&A + 데이터 수집~DB
> 구축 풀 파이프라인)은 git **태그 `v1.0.0`** 에 보존되어 있다. 그 chroma_db를 동봉해
> 멀티턴(2.0.1) → API/UI(2.2.0) → **에이전트화(2.6.0)** 로 발전시킨 후속 버전이며 독립 동작한다.

현재 버전: **2.6.0** (LangGraph 에이전트화 — RAG를 tool로 편입 + PubMed 라이브 검색).

---

## 기술 스택

| 구성요소 | 기술 |
|---|---|
| 에이전트 | LangGraph tool-calling agent (`langchain.agents.create_agent`) |
| Tools | `search_local_corpus`(ChromaDB) · `search_pubmed_live`(Entrez) |
| Embedding (쿼리) | PubMedBERT (`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`) |
| Vector DB | ChromaDB (`PersistentClient`, 동봉된 `chroma_db/`) |
| LLM | Ollama — `gemma4:31b`(품질) / `gemma4:26b`(개발). *stock gemma3는 tool-calling 미지원* |
| 대화 기억 | `SqliteSaver` 체크포인터(thread_id별) + `application_logs` 로깅 |
| Backend / Frontend | FastAPI / Streamlit |

---

## 아키텍처

```
브라우저 ─ Streamlit(06_ui :8501) ─HTTP POST /chat→ FastAPI(05_api :8000)
                                                       │
                            get_agent(02): create_agent + SqliteSaver 체크포인터(03)
                                                       │  tool 오케스트레이션
                       ┌───────────────────────────────┴───────────────────────────────┐
               search_local_corpus                                            search_pubmed_live
        retriever(01) → 동봉 chroma_db (5,590편)                            Entrez → PubMed 전체
```

폴더 번호: `01 검색(tool 본체) → 02 에이전트 → 03 기억`, 서비스 노출 `05 API → 06 UI`.
CLI(`04_interface/chat.py`)는 API 없이 같은 에이전트를 직접 호출한다. 멀티턴 질문 재작성은
별도 체인 없이 에이전트가 대화기록을 보고 tool 쿼리를 스스로 형성한다.

---

## 디렉터리 구조

```
RAG-LLM_ver2.0.0/
├── config.py                    # 공유 설정: chroma_db 경로, 모델명, AGENT_SYSTEM_PROMPT, NCBI
├── requirements.txt
├── run_app.sh                   # FastAPI(:8000) + Streamlit(:8501) 동시 기동
├── chroma_db/                   # 동봉 벡터 DB (PubMed 5,590편, PubMedBERT 임베딩)
├── 00_Docs/                     # 학습 노트 + 버전별 PLAN/VERIFY
├── 01_retrieval/
│   └── pubmedbert_retriever.py  # PubMedBERT 쿼리 임베딩 → chroma 검색 (search_local_corpus 본체)
├── 02_chain/
│   ├── tools.py                 # search_local_corpus + search_pubmed_live (@tool)
│   └── agent.py                 # get_agent: create_agent + 2 tool + SqliteSaver, steps/pmids 추출
├── 03_memory/
│   └── db_utils.py              # application_logs 로깅 SQLite (*.db는 gitignore)
├── 04_interface/
│   └── chat.py                  # CLI 멀티턴 루프
├── 05_api/
│   ├── main.py                  # FastAPI: POST /chat (에이전트 모델별 캐시, steps 반환)
│   └── models.py                # pydantic QueryInput / QueryResponse(+steps)
└── 06_ui/
    ├── streamlit_app.py         # 진입점, session_state 초기화
    ├── chat_interface.py        # 말풍선 + 🔧도구 호출 + 검색 PMID expander
    ├── api_utils.py             # /chat HTTP 클라이언트
    └── sidebar.py               # 모델 선택 + 새 세션
```

---

## 셋업

```bash
# 1. 의존성 (저장소 루트의 .venv 재사용)
../.venv/bin/python -m pip install -r requirements.txt

# 2. Ollama 모델 (로컬 실행 중이어야 함; tool-calling 지원 모델 필요)
ollama list          # gemma4:31b(품질) / gemma4:26b(개발) 확인

# 3. (선택) PubMed 라이브 검색 rate limit 완화
export NCBI_EMAIL="you@example.com"   # 권장
export NCBI_API_KEY="..."             # 선택 (3→10 req/s)
```

PubMedBERT는 첫 실행 시 자동 다운로드(~500MB). chroma_db는 동봉되어 별도 빌드 불필요.

---

## 실행

```bash
# 웹 (FastAPI + Streamlit 동시 기동)
./run_app.sh                     # → http://localhost:8501

# CLI
../.venv/bin/python 04_interface/chat.py          # 품질 모델 (gemma4:31b)
../.venv/bin/python 04_interface/chat.py --dev    # 개발 모델 (gemma4:26b, 빠름)
```

`NN_` 폴더는 숫자로 시작해 `import`가 안 되므로, 진입점(`chat.py`/`main.py`)에서만
각 스테이지를 `sys.path`에 등록한다.

---

## 동작 (검증 시나리오)

```
S1 (로컬 RAG):   "What antimicrobial activity does shrimp shell chitosan have?"
                 → search_local_corpus → 코퍼스 PMID 인용
S2 (라이브):     "Find the latest 2024+ PubMed papers on fish bone collagen peptides"
                 → search_pubmed_live → 코퍼스 밖 최신 PMID
S3 (멀티턴):     Q1 후 "What about its antioxidant effects?"  (대명사)
                 → 체크포인터가 'its' 해소 → 올바른 tool 쿼리
```

각 답변에 tool 호출(🔧)과 인용 PMID가 노출된다. 측정 결과는
[`00_Docs/version_management/ver2.6.0_+LangGraph-Agent/VERIFY.md`] 참고.

---

## 버전 로드맵

| 버전 | 내용 | 상태 |
|---|---|---|
| 2.0.1 | Multi-turn + LangChain + Ollama 전환 | ✅ 완료 (tag `v2.0.1`) |
| 2.2.0 | API + UI (FastAPI + Streamlit) | ✅ 완료 (tag `v2.2.0`) |
| 2.6.0 | LangGraph 에이전트화 — RAG를 tool로 편입 + PubMed 라이브 검색 | ✅ 완료 (tag `v2.6.0`) |
| 2.4.0 | user config, id/pw | 예정 |
| 2.5.0 | server deploy | 예정 |

**스핀오프** (메인 라인 밖, 별도 태그 네임스페이스):

| 버전 | 내용 | 상태 |
|---|---|---|
| 2.6.0-mcp.1 | MCP 서버화 — 검색 tool 2개를 MCP(stdio)로 노출 (`07_mcp/`) | ✅ 완료 (tag `v2.6.0-mcp.1`) |

품질 평가(RAGAS), 검색 고도화(re-ranking, hybrid, 코사인 전환), 응답 스트리밍은 향후 과제.
