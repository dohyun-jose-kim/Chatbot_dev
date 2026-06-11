# ver2.2.0 — API + UI (FastAPI + Streamlit) 통합 구현 계획

> KickStart 로드맵의 `2.2.0 UI` + `2.3.0 app`을 **하나로 통합**한다.
> 이유: FastAPI는 로드맵상(2.3.0 app, 2.5.0 deploy) 확정적으로 도입되므로,
> UI를 in-process로 먼저 만들면 2.3.0에서 HTTP로 갈아엎는 throwaway가 생긴다.
> 처음부터 Streamlit이 FastAPI를 거치게 하면 버리는 배선이 없다.
> 버전 번호는 "일단 둔다" 방침에 따라 2.2.0으로 두되, 2.3.0 범위를 흡수함을 명시.
> 직전 버전: [`../ver2.0.1_+Multi-turn+LangChain/PLAN.md`].

## 목표

2.0.1의 멀티턴 RAG 로직(01~03 스테이지)을 **FastAPI 백엔드**로 노출하고,
**Streamlit 프론트엔드**가 HTTP로 그 백엔드를 호출하는 클라이언트/서버 구조를 만든다.
체인·검색·기억은 재사용, 새로 만드는 건 API 레이어와 웹 UI뿐.

**성공 기준 (검증 시나리오)**
FastAPI 가동 후 브라우저에서 멀티턴 통과:
```
Q1: "What bioactivities does fish scale collagen have?"
Q2: "What about its antioxidant effects?"   ← 대명사 추적
```
- 채팅 말풍선 누적, Q2에서 'its' 해소되어 답 변화
- 각 답변에 PMID 인용 + "검색된 PMID" 펼침(expander)
- 사이드바에서 모델(gemma4:31b / gemma3:4b) 전환, '새 세션' 버튼
- UI↔API가 HTTP(`localhost:8000/chat`)로 통신 (curl로도 같은 응답)

## 아키텍처

```
브라우저 ── Streamlit(06_ui, :8501) ──HTTP POST /chat──> FastAPI(05_api, :8000)
                                                              │
                                          get_rag_chain(02) + db_utils(03) + retriever(01)
                                                              │
                                                      ver1 chroma_db (읽기 전용)
```
Streamlit의 HTTP 요청은 Streamlit 서버(파이썬, `requests`)가 보내므로 브라우저 CORS 무관.

## 핵심 설계 결정

### 1. FastAPI는 모델별 체인을 1회 로드해 캐시
레퍼런스 `main.py`는 요청마다 `get_rag_chain()`을 새로 만든다(OpenAI라 로컬 로드 없음).
우리는 `get_rag_chain`이 PubMedBERT(MPS) 로드 + Ollama 연결을 하므로 요청마다 재로드는 치명적.
→ API에서 `@lru_cache(model)` 또는 모듈 dict로 체인을 모델별 1회 로드해 재사용.

### 2. 모델 선택은 요청 본문으로 전달
레퍼런스처럼 `QueryInput.model`로 UI→API 전달. enum을 gemma용으로 교체
(`gemma4:31b`, `gemma3:4b`). 기본값은 빠른 `gemma3:4b`.

### 3. 세션/기억은 기존 SQLite 그대로
API가 `session_id` 없으면 uuid 발급 후 응답에 포함, UI는 `st.session_state`에 보관.
대화기록 영속은 `03_memory/db_utils.py`(SQLite) 재사용 — CLI/UI/API가 같은 기억 백엔드 공유.

### 4. 응답에 검색 PMID 포함
레퍼런스 `QueryResponse`(answer, session_id, model)에 `pmids: list[str]` 추가.
체인 결과 `out["context"]`의 metadata에서 추출 → UI expander로 표시.

### 5. 문서 업로드 기능 제거
upload/list/delete-doc 엔드포인트와 사이드바 업로드 UI 모두 제외(고정 코퍼스).

## 빌려오는 것

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| ref `api/main.py` | `/chat` 엔드포인트 흐름(session_id 처리, 기록 조회→invoke→저장) | OpenAI 제거, 체인 캐시, upload/delete 엔드포인트 삭제, pmids 반환 |
| ref `api/pydantic_models.py` | QueryInput/QueryResponse | ModelName enum을 gemma로, QueryResponse에 pmids 추가, Document/Delete 모델 삭제 |
| ref `app/api_utils.py` | `get_api_response()` HTTP 클라이언트 | upload/list/delete 함수 삭제 |
| ref `app/chat_interface.py` | 말풍선 렌더링 + 입력 처리 | pmids expander 추가 |
| ref `app/sidebar.py` | 모델 셀렉트 | 업로드/문서목록 제거, gemma 모델, '새 세션' 버튼 |
| ref `app/streamlit_app.py` | 진입점, session_state 초기화 | 제목/구성 우리 것 |
| ver2.0.1 `01~03` | 체인·검색·기억 | 그대로 import |

## 파일 구성 (구현 시)

```
RAG-LLM_ver2.0.0/
├── 01_retrieval/ 02_chain/ 03_memory/   # 재사용 (변경 없음)
├── 04_interface/chat.py                 # CLI (그대로)
├── 05_api/
│   ├── main.py                          # FastAPI: POST /chat (uvicorn)
│   └── models.py                        # pydantic QueryInput/QueryResponse
├── 06_ui/
│   ├── streamlit_app.py                 # 진입점
│   ├── chat_interface.py                # 말풍선 + pmids expander
│   ├── api_utils.py                     # /chat HTTP 클라이언트
│   └── sidebar.py                       # 모델 선택 + 새 세션
└── run_app.sh                           # uvicorn + streamlit 동시 기동
```
requirements에 `fastapi`, `uvicorn`, `streamlit`, `requests` 추가. 루트 `.venv` 재사용.

## 구현 순서 (각 단계 검증 포함)

```
1. requirements 추가 + 05_api/ 06_ui/ 골격
   → verify: uvicorn으로 빈 FastAPI /docs 뜸, streamlit 빈 앱 뜸

2. 05_api/main.py + models.py — /chat (체인 모델별 캐시, db 연결)
   → verify: curl POST /chat → answer+pmids+session_id 반환,
            반환된 session_id로 재요청 시 멀티턴(대명사 추적) 동작

3. 06_ui — api_utils + streamlit_app + chat_interface (단일턴)
   → verify: 브라우저 질문 1개 → PMID 인용 답변 + 검색 PMID expander

4. 멀티턴 session_state + sidebar(모델, 새 세션) + run_app.sh
   → verify: Q1→Q2 대명사 추적 브라우저 통과 @ gemma3:4b, 모델 전환·새 세션 동작

5. (선택) gemma4:31b 동작 + 스피너/지연 UX 점검
```

## 범위 제외

- 사용자 인증/멀티유저 (2.4.0), 서버 배포 (2.5.0)
- 답변 스트리밍(토큰 단위), 문서 업로드/관리

## 리스크

- **두 프로세스 기동**: uvicorn + streamlit. `run_app.sh`로 묶고, API 헬스 확인 후 UI 띄움.
- **체인 캐시 누락**: API가 요청마다 PubMedBERT 재로드하면 치명적 → 모델별 1회 로드 캐시 필수.
- **31b 지연**: 턴당 60~70초(VERIFY.md). 기본 gemma3:4b, 31b는 선택. UI는 `st.spinner`,
  API는 요청 타임아웃 넉넉히(예: requests timeout 300s).
- **chroma 부작용**: 2.0.1과 동일 — 쿼리가 ver1 sqlite 건드림. 런타임 무해, 커밋 금지.
