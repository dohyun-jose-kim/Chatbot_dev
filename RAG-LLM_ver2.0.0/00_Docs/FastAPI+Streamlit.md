# FastAPI + Streamlit 학습 노트

ver2.2.0에서 채택한 **FastAPI(백엔드) + Streamlit(프론트엔드)** 2-tier 구조를
"왜 이렇게 나누는가"부터 우리 코드(`05_api/`, `06_ui/`)에 어떻게 적용했는지까지 정리한 공부용 문서.

---

## 1. 왜 둘을 결합하는가

두 도구는 잘하는 일이 다르다. 합치면 **각자 잘하는 것만** 맡는 구조가 된다.

| | FastAPI (백엔드) | Streamlit (프론트엔드) |
|---|---|---|
| 역할 | 무거운 계산, DB 질의, **AI 모델 추론** | 입력창·버튼·사이드바·시각화 |
| 강점 | 비동기 동시성, Pydantic 자동 검증, 자동 API 문서 | 순수 Python으로 UI, HTML/CSS/JS 불필요 |
| 비유 | 주방(요리) | 홀(서빙·손님 응대) |

핵심은 **관심사 분리(separation of concerns)**: UI를 바꿔도 백엔드가 안 흔들리고,
모델 로직을 바꿔도 화면이 안 깨진다. 그리고 백엔드는 다른 프론트엔드(모바일, 다른
마이크로서비스)가 **재사용**할 수 있는 독립 API로 남는다.

> "Decoupled Architecture: Separating them ensures that your frontend stays lightweight
> while your API remains highly reusable by other microservices or mobile." — cold-soup.tistory

---

## 2. FastAPI 기초 — 무엇으로 이루어졌나

FastAPI는 단독 프레임워크가 아니라 몇 부품의 조합이다:

- **Starlette**: ASGI 웹 프레임워크 토대(라우팅, 미들웨어).
- **Uvicorn**: ASGI 서버. HTTP 요청을 받아 앱에 넘기고 응답 수명주기를 관리. 워커 하나로
  수천 동시 연결 처리 가능. (`uvicorn main:app`)
- **Pydantic**: 요청/응답을 BaseModel로 정의 → JSON ↔ Python 객체 **자동 변환·검증**.
  타입이 안 맞으면 422 에러를 자동 반환.
- **Swagger UI / ReDoc**: 타입 힌트 + Pydantic으로 **OpenAPI 문서 자동 생성**.
  `/docs`(Swagger), `/redoc`에서 바로 테스트 가능 — 별도 작업 0.

**ASGI vs WSGI**: 전통적 WSGI(Flask 등)는 요청을 동기 처리. ASGI는 `async`/`await`로
여러 요청을 동시에 처리 → I/O 대기(모델 추론, DB)가 많은 앱에 유리.

---

## 3. Streamlit 기초 — 왜 프론트로 쓰나

- **속도**: UI를 분 단위로 만들고 고친다. HTML/CSS/JS 컨텍스트 스위칭 없음.
- **Python-first**: 데이터 사이언티스트의 스킬셋(Python)에 그대로 머문다.
- **데이터 친화**: 표·차트·레이아웃 컴포넌트 내장.
- **주의할 동작 모델**: Streamlit은 **상호작용마다 스크립트 전체를 위→아래로 재실행**한다.
  그래서 무거운 객체(모델, 커넥션)는 캐시(`@st.cache_resource`)하거나, 우리처럼
  **백엔드에 둬서** 매 재실행에 영향받지 않게 해야 한다.

---

## 4. 둘을 잇는 법 — `requests`로 HTTP 호출

Streamlit은 `requests`로 FastAPI 엔드포인트를 호출하는 **얇은 클라이언트**가 된다.
버튼 클릭/입력 시점에만 요청을 보내 불필요한 호출을 피한다(특히 ML 앱에서 비용 절감).

```python
# 일반 패턴 (pybit.es 예시 요약)
import requests, streamlit as st
API_URL = "http://localhost:8000"
resp = requests.post(f"{API_URL}/chat", json={"question": q, "model": m}, timeout=300)
if resp.status_code == 200:
    data = resp.json()
```

### CORS는 언제 문제가 되나
`requests`로 보내는 호출은 **Streamlit 서버(파이썬 프로세스)**가 보내는 서버-사이드
요청이라 브라우저 CORS와 무관하다. CORS는 **브라우저 JS가 다른 도메인의 API를
직접 fetch**할 때 발생한다. 프론트/백이 다른 도메인에 배포돼 브라우저가 직접 호출하면
FastAPI에 `CORSMiddleware`로 허용 도메인을 명시해야 한다:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["https://your-streamlit-app"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```

> 우리 ver2.2.0은 Streamlit 서버가 `requests`로 호출하므로 **현재 CORS 설정 불필요**.
> 단, 추후 배포(2.5.0)에서 브라우저가 API를 직접 치는 구성이 되면 추가해야 한다.

---

## 5. 장단점 정리

**장점**
- 관심사 분리 — 프론트/백 변경이 서로 전파되지 않음
- 재사용성 — 같은 백엔드를 여러 프론트엔드가 공유
- 전문화 — 각자 잘하는 일(UI vs API)에 집중
- 독립 확장 — 프론트/백을 자원 요구에 따라 따로 스케일
- 개발 속도 — 현대적 백엔드 + 빠른 UI

**단점**
- **로컬 개발 번거로움**: 서버 둘(uvicorn + streamlit)을 항상 띄워야 함. 프론트만 만질
  때도 백엔드가 떠 있어야 함 → 우리는 `run_app.sh`로 묶어 완화.
- 네트워크 홉 추가(HTTP 직렬화/역직렬화) — 로컬에선 무시할 수준.

---

## 6. 우리 프로젝트(ver2.2.0) 적용

```
브라우저 ─ Streamlit(06_ui, :8501) ─HTTP POST /chat→ FastAPI(05_api, :8000)
                                                          │
                                  get_rag_chain(02) + db_utils(03) + retriever(01)
                                                          │
                                                  ver1 chroma_db (읽기 전용)
```

| 일반 가이드의 개념 | 우리 코드에서 | 우리만의 결정 |
|---|---|---|
| FastAPI가 무거운 추론 담당 | `05_api/main.py` `/chat` | **모델별 체인 `@lru_cache`** — 요청마다 PubMedBERT(MPS) 재로드 방지 |
| Pydantic 검증 | `05_api/models.py` `QueryInput/QueryResponse` | `ModelName` enum을 gemma로, 응답에 `pmids` 추가 |
| Streamlit이 `requests`로 호출 | `06_ui/api_utils.py` `get_api_response` | 31b 지연 대비 `timeout=300` |
| 버튼/입력 시점에만 호출 | `06_ui/chat_interface.py` `st.chat_input` | 검색 PMID를 `st.expander`로 노출 |
| session 상태 관리 | `st.session_state`(messages, session_id, model) | 영속 기억은 백엔드 SQLite(`03_memory`) 공유 |
| 자동 문서 | `http://localhost:8000/docs` | curl/Swagger로 UI 없이도 검증 |

**왜 UI(2.2.0)와 API(2.3.0)를 한 버전으로 합쳤나**: FastAPI는 로드맵상 확정 도입이라,
UI를 먼저 in-process로 만들면 나중에 HTTP로 갈아엎는 throwaway가 생긴다. 처음부터
2-tier로 가면 버리는 배선이 없다. (자세히는
[`version_management/ver2.2.0_+API+UI/PLAN.md`](version_management/ver2.2.0_+API+UI/PLAN.md))

**실행**
```bash
cd RAG-LLM_ver2.0.0 && ./run_app.sh   # uvicorn(:8000) + streamlit(:8501) 동시 기동
```

---

## 7. 더 알아보기 (배포·운영)

- **환경변수/시크릿**: `pydantic-settings`의 `BaseSettings`로 `.env`(로컬) / `os.environ`
  (서버) / `st.secrets`(Streamlit Cloud)를 한 곳에서 로드 — 하드코딩 회피.
- **Docker**: 백엔드를 컨테이너화하면 로컬·배포 환경이 동일하게 동작 → 일관성/이식성.
  (우리 로드맵 2.5.0 server deploy에서 다룰 주제)
- **확장**: FastAPI의 의존성 주입(dependency injection)으로 DB 세션·인증을 모듈화 —
  2.4.0(user config, id/pw)에서 활용 가능.

---

## 참고 자료

- [cold-soup.tistory.com/349 — FastAPI+Streamlit](https://cold-soup.tistory.com/349)
- [Pybites — From Backend to Frontend: Connecting FastAPI and Streamlit](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/)
- [Towards Data Science — FastAPI and Streamlit: The Python Duo You Must Know About](https://towardsdatascience.com/fastapi-and-streamlit-the-python-duo-you-must-know-about-72825def1243/)
- [TestDriven.io — Serving a Machine Learning Model with FastAPI and Streamlit](https://testdriven.io/blog/fastapi-streamlit/)
- [DEV — Understanding FastAPI Fundamentals (Uvicorn, Starlette, Swagger, Pydantic)](https://dev.to/kfir-g/understanding-fastapi-fundamentals-a-guide-to-fastapi-uvicorn-starlette-swagger-ui-and-pydantic-2fp7)
- [Uvicorn — ASGI 개념](https://uvicorn.dev/concepts/asgi/)
- [PrepVector — Deploying a Two-Tier RAG Chatbot with FastAPI and Streamlit](https://prepvector.substack.com/p/deploying-a-two-tier-rag-chatbot)
