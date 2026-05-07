좋아요. "가장 기초적인 RAG 챗봇"이 동작하기 위해 필요한 것을 빠짐없이, 계층별로 정리할게요.

# 전체 아키텍처: 5개 계층
사용자 입력
   ↓
[1] UI 계층 — 입력 수신, 응답 출력
   ↓
[2] 세션/메모리 계층 — 대화 이력 저장·조회
   ↓
[3] 검색 계층 — 벡터 DB에서 관련 문서 검색
   ↓
[4] 프롬프트 조립 계층 — 시스템 프롬프트 + 검색 결과 + 대화 이력 + 현재 질문 → 하나의 프롬프트로 합성
   ↓
[5] 생성 계층 — LLM API 호출 → 응답 반환
   ↓
응답을 [2]에 저장하고 [1]로 출력
각 계층에서 반드시 결정해야 하는 것과 최소 구현을 정리합니다.

## [1] UI 계층
역할: 사용자의 텍스트 입력을 받고, LLM 응답을 화면에 보여줌.

### 필수 결정 사항

프레임워크 선택 — 최소 구현이면 Streamlit. st.chat_input()으로 입력, st.chat_message()로 출력.
대화 렌더링 — 이전 메시지들을 화면에 순서대로 다시 그려줘야 함. Streamlit은 매 rerun마다 전체 화면을 다시 그리기 때문에, st.session_state.messages를 순회하며 렌더링하는 루프가 필요.
스트리밍 여부 — 최소 구현에서는 생략 가능. 응답이 다 생성된 후 한 번에 출력.

### 최소 구현물
Streamlit 스크립트 1개 (app.py)

## [2] 세션/메모리 계층
역할: "이 사용자가 지금까지 뭘 말했고, 봇이 뭘 답했는가"를 유지.

### 필수 결정 사항

메모리 전략 — Buffer Memory (전체 이력 그대로 유지). 가장 단순.
저장 구조 — 메시지 리스트. 각 메시지는 {"role": "user" | "assistant", "content": "..."} 형태.
저장소 — Streamlit의 st.session_state (인메모리). 브라우저 탭 = 1세션. 서버 재시작 시 소멸.
토큰 한도 대응 — 최소 구현에서는 무시하되, 설계상 "메시지가 N턴을 초과하면 오래된 것부터 제거"하는 조건을 코드에 자리만 만들어 둠.

### 최소 구현물
pythonif "messages" not in st.session_state:
    st.session_state.messages = []

## [3] 검색 계층
역할: 사용자 질문과 의미적으로 가까운 문서 chunk를 벡터 DB에서 꺼내옴.

### 사전 작업 (오프라인, 1회성)

원본 문서 수집 — 예: PubMed 초록 6,000건, CSV/JSON 형태
청킹 전략 결정 — 초록 단위(full-abstract chunking)면 1 문서 = 1 chunk. 긴 문서면 500~1000 토큰 단위로 분할하되 overlap 50~100 토큰.
임베딩 모델 선택 — OpenAI text-embedding-3-small 또는 오픈소스 sentence-transformers/all-MiniLM-L6-v2. 결정 기준: API 비용 vs 로컬 실행 가능 여부.
벡터 DB 선택 — 최소 구현이면 Chroma (로컬, 파일 기반, 설치 한 줄). 영속성 필요하면 persist_directory 지정.
인덱싱 — 모든 chunk를 임베딩해서 벡터 DB에 저장. 메타데이터(출처, 제목 등)도 함께.

### 런타임 작업 (매 질문마다)

사용자 질문을 같은 임베딩 모델로 벡터화
벡터 DB에서 cosine similarity 상위 k개 chunk 반환 (k=3~5가 기본)
각 chunk의 텍스트와 메타데이터를 다음 계층으로 전달

### 필수 결정 사항

임베딩 모델 (어떤 모델, 차원 수)
k 값 (몇 개 chunk를 가져올 것인가)
similarity threshold 적용 여부 (최소 구현에서는 생략 가능)

### 최소 구현물
vectorstore = Chroma.from_documents(docs, embedding) + vectorstore.similarity_search(query, k=3)

## [4] 프롬프트 조립 계층
역할: LLM에게 보낼 최종 프롬프트를 하나로 합성. 이 계층이 RAG 챗봇의 핵심 설계 지점.

### 프롬프트 구성 요소 (순서대로)
[A] 시스템 프롬프트 (system)
    — 봇의 역할, 답변 규칙, 톤, 제약 조건 정의
    — 예: "당신은 해양 부산물 건강기능식품 연구 어시스턴트입니다.
           아래 [참고 문서]에 근거해서만 답변하세요.
           근거가 없으면 '해당 정보를 찾지 못했습니다'라고 답하세요."

[B] 검색된 문서 (system 또는 user 메시지에 삽입)
    — [3]에서 가져온 chunk들을 포맷팅
    — 예: "[참고 문서 1] {chunk_text_1}\n[참고 문서 2] {chunk_text_2}\n..."

[C] 대화 이력 (messages 배열)
    — [2]에서 가져온 과거 user/assistant 메시지 전체

[D] 현재 사용자 질문 (user)
    — 이번 턴의 입력
LLM API에 보내는 최종 형태:
pythonmessages = [
    {"role": "system", "content": system_prompt + "\n\n" + formatted_docs},
    *conversation_history,   # [C]
    {"role": "user", "content": current_question}   # [D]
]
### 필수 결정 사항

시스템 프롬프트 문구 (답변 톤, 할루시네이션 방지 지시, 출처 인용 방식)
검색 결과를 어디에 넣을 것인가 (system에 넣는 게 일반적)
검색 결과 포맷 (번호 매기기, 구분선 등)


## [5] 생성 계층
역할: 조립된 프롬프트를 LLM API에 보내고 응답을 받아옴.

### 필수 결정 사항

LLM 선택 — OpenAI gpt-4o-mini (가격 대비 성능), Claude claude-sonnet-4-20250514, 또는 로컬 모델
API 호출 파라미터 — temperature (사실 기반이면 0~0.3), max_tokens
에러 핸들링 — API 타임아웃, rate limit 대응 (최소 구현이면 try-except로 메시지 출력)

### 최소 구현물
pythonresponse = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=assembled_messages,
    temperature=0.2
)
answer = response.choices[0].message.content

## 전체 실행 흐름 (1턴 기준)
1. 사용자가 UI에 질문 입력                          [1]
2. st.session_state.messages에 user 메시지 append   [2]
3. 질문을 임베딩 → 벡터 DB 검색 → top-k chunk 반환   [3]
4. system_prompt + 검색 결과 + 대화 이력 + 질문 조립   [4]
5. LLM API 호출 → 응답 수신                         [5]
6. 응답을 st.session_state.messages에 append         [2]
7. 응답을 화면에 렌더링                              [1]
→ 다음 질문 대기 (1로 돌아감)

