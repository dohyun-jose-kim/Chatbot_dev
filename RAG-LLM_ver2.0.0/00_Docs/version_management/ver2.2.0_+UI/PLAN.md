# ver2.2.0 — UI (Streamlit) 구현 계획

> 버전 번호: KickStart 로드맵의 `ver2.2.0 == UI`를 따름. (멀티턴이 실제로는 2.0.1로
> 출시되어 번호 체계가 어긋나 있으나, "버전 이름은 일단 둔다" 방침에 따라 추후 정리.)
> 직전 버전(멀티턴 + LangChain + Ollama)은 [`../ver2.0.1_+Multi-turn+LangChain/PLAN.md`].

## 목표

2.0.1에서 만든 멀티턴 RAG(CLI)를 **Streamlit 웹 채팅 UI**로 감싼다.
체인·검색·기억 로직(01~03 스테이지)은 그대로 재사용하고, 04_interface의 CLI와
나란히 서는 또 하나의 인터페이스(`05_ui/`)를 추가한다.

**성공 기준 (검증 시나리오)**
브라우저에서 멀티턴 시나리오 통과:
```
Q1: "What bioactivities does fish scale collagen have?"
Q2: "What about its antioxidant effects?"   ← 대명사 추적
```
- 채팅 말풍선으로 대화가 누적되고, Q2에서 'its'가 해소되어 답이 바뀜
- 각 답변에 PMID 인용 + "검색된 PMID" 펼침(expander) 표시
- 사이드바에서 모델(gemma4:31b / gemma3:4b) 전환 가능

## 핵심 설계 결정

### 1. UI는 체인을 in-process로 직접 호출 (FastAPI 미도입)
레퍼런스 레포의 Streamlit은 `get_api_response()`로 **FastAPI(8000)**를 거친다.
하지만 KickStart는 UI(2.2.0)와 app/FastAPI(2.3.0)를 분리한다.
→ 2.2.0에서는 `api_utils.py`(HTTP)를 **버리고**, Streamlit에서 `get_rag_chain()`과
`db_utils`를 직접 import해 `chain.invoke(...)` 호출. 클라이언트/서버 분리는 2.3.0에서.

### 2. 체인은 `@st.cache_resource`로 1회 로드
Streamlit은 상호작용마다 스크립트를 전체 재실행한다. 매번 모델을 다시 로드하면
(PubMedBERT + Ollama, 특히 31b) 치명적으로 느려진다.
→ `get_rag_chain(model)`을 `@st.cache_resource(model별)`로 캐시. 모델 전환 시에만 재로드.

### 3. 문서 업로드 기능 제거
레퍼런스 사이드바의 upload/list/delete-doc은 ver1 고정 코퍼스(PubMed 5,590편)를
쓰는 우리 구조엔 불필요. 사이드바는 **모델 선택 + 새 세션 버튼**만.

### 4. 세션/기억
`st.session_state`에 `messages`(말풍선용)와 `session_id`(uuid) 보관.
영속 대화기록은 기존 `03_memory/db_utils.py`(SQLite, session_id 키) 재사용 — UI도 CLI와
같은 기억 백엔드를 공유.

## 빌려오는 것

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| references/conversational-rag-chatbot `app/chat_interface.py` | 채팅 말풍선 렌더링 + 입력 처리 패턴 | `get_api_response` → `chain.invoke` 직접 호출 |
| references/conversational-rag-chatbot `app/streamlit_app.py` | 앱 진입점, session_state 초기화 | 제목/구성 우리 것으로 |
| references/conversational-rag-chatbot `app/sidebar.py` | 사이드바 모델 셀렉트 패턴 | 업로드/문서목록 제거, 모델을 gemma로, '새 세션' 버튼 추가 |
| ver2.0.1 `02_chain/rag_chain.py`, `03_memory/db_utils.py` | 체인·기억 로직 | 그대로 import (in-process) |

## 파일 구성 (구현 시 — 05_ui/ 신설)

```
RAG-LLM_ver2.0.0/
├── 01_retrieval/ 02_chain/ 03_memory/   # 재사용 (변경 없음)
├── 04_interface/chat.py                 # CLI (그대로)
└── 05_ui/
    ├── streamlit_app.py                 # 진입점: streamlit run 05_ui/streamlit_app.py
    ├── chat_interface.py                # 말풍선 + chain.invoke
    └── sidebar.py                       # 모델 선택 + 새 세션
```
import 부트스트랩은 CLI와 동일(진입점에서 sys.path에 01~03 등록).
requirements.txt에 `streamlit` 추가, 루트 `.venv` 계속 재사용.

## 구현 순서 (각 단계 검증 포함)

```
1. requirements에 streamlit 추가 + 05_ui/ 골격
   → verify: streamlit run으로 빈 앱 뜸

2. streamlit_app.py + chat_interface.py — 단일턴 in-process
   → verify: 질문 1개 입력 → PMID 인용 답변 + 검색 PMID expander 표시

3. 멀티턴 + session_state + db_utils 연결
   → verify: Q1→Q2 대명사 추적 시나리오 브라우저에서 통과 @ gemma3:4b

4. sidebar.py — 모델 선택 + 새 세션, @st.cache_resource
   → verify: 모델 전환 시에만 재로드, '새 세션'으로 기억 초기화 확인

5. (선택) gemma4:31b 동작 확인 — 스피너/지연 UX 점검
```

## 범위 제외

- FastAPI 서버 (2.3.0), 사용자 인증 (2.4.0), 배포 (2.5.0)
- 문서 업로드/관리, 멀티 유저
- 답변 스트리밍(토큰 단위 출력)은 일단 제외 — 필요하면 별도

## 리스크

- **31b 대화형 지연**: 턴당 60~70초(VERIFY.md). UI에선 `st.spinner`로 대기 표시하되,
  기본 모델을 gemma3:4b로 두는 것을 권장. 31b는 선택지로만.
- **Streamlit 재실행 모델**: 캐시(`@st.cache_resource`) 누락 시 매 입력마다 모델 재로드 →
  반드시 캐시. PubMedBERT(MPS) + Ollama 커넥션 모두 캐시 대상.
- **chroma 부작용**: 2.0.1과 동일 — 쿼리가 ver1 sqlite를 건드림. 런타임 무해, 커밋 금지.
