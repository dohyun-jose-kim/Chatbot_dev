# ver2.6.0 — LangGraph 에이전트화 (RAG를 tool로 편입) 구현 계획

> 직전 버전: [`../ver2.2.0_+API+UI/PLAN.md`]. 로드맵상 2.4.0(인증)·2.5.0(배포)보다 **먼저** 진행.
> 이유: 에이전트는 코어 변경이라 iteration이 싼 로컬에서 끝내야 하고, tool-calling 모델 결정이
> 배포(2.5.0) 모델·비용 결정의 입력이 되기 때문(개발 순서 논의 결론).

## 목표

ver2.2.0의 **고정 체인**(`create_history_aware_retriever` + `create_retrieval_chain`)을
**tool-calling 에이전트**로 교체한다. 기존 검색을 tool 하나로 편입하고, PubMed 라이브 검색
tool을 추가해 "코퍼스 먼저, 부족하면 라이브"라는 오케스트레이션을 구현한다.

- **고정 체인 → tool-calling agent** (LangChain v1 prebuilt `create_agent`)
- **2개 tool**: `search_local_corpus`(동봉 5,590편) + `search_pubmed_live`(Entrez, 코퍼스 밖)
- 멀티턴: 질문 재작성 체인을 **에이전트가 흡수**(대화기록 보고 tool 쿼리를 스스로 형성)
- UI에 **tool 호출(이름·쿼리) 노출**

## 사전 검증 (완료)

| 항목 | 결과 |
|---|---|
| `create_agent` 전체 ReAct 루프 (stub tool, `gemma4:26b`) | ✅ 질문→tool 호출→결과→PMID 인용 답변, **5.5s** |
| tool-calling 모델 | ✅ `gemma4:31b`(quality)·`gemma4:26b`·`qwen3:14b/32b` / ❌ `gemma3:4b`·`exaone3.5` (400 "does not support tools") |
| import 변경 (LangChain v1) | `langgraph.prebuilt.create_react_agent` → **`from langchain.agents import create_agent`** (deprecation 확인) |

→ 호스티드 API 불필요, quality 모델 유지, **dev 모델만 교체**하면 됨.

## 성공 기준 (검증 시나리오)

```
S1 (로컬 RAG 패리티): "What antimicrobial activity does shrimp shell chitosan have?"
   → search_local_corpus 호출 → 코퍼스 PMID 인용 답변
S2 (오케스트레이션/라이브): "Find the latest 2024+ PubMed papers on fish collagen peptides"
   → search_pubmed_live 호출 → 코퍼스에 없을 수 있는 최신 PMID 반환
S3 (멀티턴 대명사): Q1 주제질문 → Q2 "What about its antioxidant effects?"
   → checkpointer 기반 history로 'its' 해소, 올바른 tool 쿼리 형성
```

세 시나리오 모두 (a) 적절한 tool 선택, (b) PMID 인용 유지, (c) **UI에 tool 호출 표시**되면 성공.

## 빌려오는 것 (직접 구현 최소화)

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| LangChain v1 `langchain.agents.create_agent` | ReAct 오케스트레이션 루프 | prebuilt 그대로 사용 (tools·prompt·checkpointer만 주입) |
| LangGraph `SqliteSaver` (`langgraph.checkpoint.sqlite`) | 세션별(thread_id) 대화 상태 영속 | `langgraph-checkpoint-sqlite` 추가 |
| ver2.0.0 `01_retrieval/pubmedbert_retriever.py` | 검색 로직 | `@tool`로 감쌈 (모델 1회 로드 싱글턴) |
| ver1 `collect_pubmed.py` (tag `v1.0.0`) | Entrez ESearch/EFetch | `search_pubmed_live` tool로 축소(retmax 소량, 에러/타임아웃 graceful) |
| ver2.0.0 `config.py` 프롬프트 | SYSTEM_PROMPT(PMID 인용) | 오케스트레이션 지시 추가 |
| ver2.0.0 `05_api` / `06_ui` | /chat·말풍선 | history 수동전달 제거(checkpointer가 대신), tool 단계 반환·표시 추가 |

## 핵심 설계 결정

### 1. 메모리: 수동 chat_history 전달 → 에이전트 checkpointer
기존엔 `get_chat_history(session_id)`로 꺼내 체인에 넣었다. 에이전트는 **`SqliteSaver` 체크포인터**가
`thread_id`별 메시지를 영속하므로, `invoke(..., config={"configurable": {"thread_id": session_id}})`만
하면 history가 자동 주입된다. → `db_utils.get_chat_history`는 더 이상 체인 입력 경로가 아님.
`insert_application_logs`(감사·로깅용)는 유지. `session_id`를 그대로 `thread_id`로 매핑.

### 2. tool 2개
- `search_local_corpus(query) -> str`: `PubMedBERTRetriever`(모듈 싱글턴, 요청마다 재로드 금지)로
  top-K 검색 → `CONTEXT_TEMPLATE` 형식 문자열(PMID/연도/저널/제목/초록) 반환.
- `search_pubmed_live(query) -> str`: Entrez ESearch+EFetch로 최신/광범위 논문 retmax≈5 반환.
  네트워크 에러·타임아웃은 메시지로 반환(에이전트 중단 금지). NCBI rate limit(키 없으면 3 req/s),
  `NCBI_API_KEY`/`NCBI_EMAIL`은 env에서.

### 3. 시스템 프롬프트 = 라우팅 지시
기존 인용 규칙 + "동봉 코퍼스(`search_local_corpus`)를 먼저 쓰고, 정보가 부족하거나 사용자가 최신/
광범위 문헌을 원하면 `search_pubmed_live`를 써라. 모든 주장에 PMID 인용, 근거 없으면 그렇게 말하라."

### 4. tool 단계 노출
`out["messages"]`에서 `AIMessage.tool_calls`(이름·args)와 `ToolMessage`를 추출해 `QueryResponse.steps`
(예: `[{tool, query}]`)로 반환. UI는 `st.status`/expander로 "🔧 search_pubmed_live('…')" 표시.
(스트리밍은 범위 제외 — 완료 후 trace 일괄 표시)

### 5. 모델
quality `gemma4:31b` 유지, **dev `gemma3:4b` → `gemma4:26b`**(tool 가능, 같은 family, `<think>` 없음).
멀티-tool 라우팅이 불안정하면 `qwen3:32b`로 교체(단 `<think>` 후처리 필요).

## 파일 구성

```
RAG-LLM_ver2.0.0/
├── config.py                       # DEV_MODEL→gemma4:26b, AGENT_SYSTEM_PROMPT, NCBI 설정
├── requirements.txt                # + langgraph-checkpoint-sqlite
├── 01_retrieval/pubmedbert_retriever.py   # 재사용(변경 없음)
├── 02_chain/
│   ├── tools.py                    # (신규) search_local_corpus + search_pubmed_live
│   ├── agent.py                    # (신규) get_agent(model): create_agent + tools + SqliteSaver
│   └── rag_chain.py                # 제거(agent.py로 대체됨)
├── 03_memory/db_utils.py           # insert_application_logs 유지, get_chat_history는 로깅조회용으로만
├── 04_interface/chat.py            # get_agent 호출, thread_id, tool 단계 출력
├── 05_api/
│   ├── main.py                     # cached_agent, /chat에 thread_id, steps 반환
│   └── models.py                   # QueryResponse에 steps 추가
└── 06_ui/chat_interface.py         # tool 단계 표시(st.status/expander)
```

## 구현 단계 (Phase별)

원칙: 각 step은 독립 검증 가능, 각 Phase는 시스템을 **동작 상태로** 남긴다(점진 증분).
Phase 끝마다 dev→main 커밋, 전체 완료 시 `tag v2.6.0`. 과도기엔 CLI(에이전트)와
API/UI(구 체인)가 잠시 공존하며 둘 다 동작 → API/UI 컷오버(Phase C) 후 구 체인 제거(Phase D).

### Phase 0 — 준비 (config + 의존성)
- **0.1** `requirements.txt`: `+ langgraph-checkpoint-sqlite`
  → verify: `from langgraph.checkpoint.sqlite import SqliteSaver` import 성공
- **0.2** `config.py`: `DEV_MODEL` `gemma3:4b`→`gemma4:26b`; `AGENT_SYSTEM_PROMPT`(PMID 인용 + 라우팅 지시) 추가; `NCBI_EMAIL`/`NCBI_API_KEY` env 로드
  → verify: `import config` OK; `gemma4:26b`·`gemma4:31b`가 `ollama list`에 존재
- **게이트**: `create_agent`(stub tool, `MemorySaver`, gemma4:26b) 단발 루프 — *이미 검증됨(5.5s)*
- **commit**: `ver2.6.0 P0: config + deps`

### Phase A — 에이전트 코어 (단일 tool = 로컬 RAG 패리티)
목표: 고정 체인을 에이전트로 대체하되 기능은 기존(로컬 RAG)과 동일. 오케스트레이션 복잡도 도입 전.
- **A.1** `02_chain/tools.py`: `search_local_corpus(query)` — `PubMedBERTRetriever` **모듈 싱글턴** 래핑(요청마다 재로드 금지), `CONTEXT_TEMPLATE` 형식(PMID/연도/저널/제목/초록) 문자열 반환
  → verify: tool 직접 호출 → ver1 retriever와 동일 top-5 PMID
- **A.2** `02_chain/agent.py`: `get_agent(model)` = `create_agent(ChatOllama(model), [search_local_corpus], system_prompt, checkpointer=MemorySaver())`
  → verify: `S1`(로컬 질문) → PMID 인용 답변
- **A.3** 멀티턴: `invoke(..., config={"configurable": {"thread_id": session_id}})`
  → verify: `S3`(대명사) — 같은 thread_id로 Q1→Q2 'its' 해소
- **A.4** `04_interface/chat.py`: `get_rag_chain`→`get_agent`, `thread_id=session_id`, **수동 chat_history 전달 제거**, tool 단계 출력
  → verify: CLI에서 `S1`·`S3` 통과
- **commit**: `ver2.6.0 PA: agent core (단일 tool, 체인 대체)`

### Phase B — 영속 메모리 + 라이브 검색 tool (오케스트레이션)
목표: 2번째 tool로 "코퍼스→라이브" 라우팅 시연 + 메모리 영속. **최대 리스크(멀티-tool 라우팅)를 여기서 retire.**
- **B.1** `MemorySaver` → `SqliteSaver`(`check_same_thread=False`)
  → verify: 프로세스 재시작 후 같은 session_id로 이전 맥락 유지
- **B.2** `02_chain/tools.py`: `search_pubmed_live(query)` — Entrez ESearch+EFetch(v1 `collect_pubmed.py` 차용, `retmax≈5`, `timeout`, 네트워크 에러는 메시지 반환)
  → verify: 라이브 질의 PMID 반환; 네트워크 차단 시 graceful(크래시 X)
- **B.3** `agent.py`: `tools=[local, live]` + 시스템 프롬프트 라우팅 지시
  → verify: `S2`(최신/광범위)→live 호출, `S1`→local 유지(오라우팅 점검)
- **commit**: `ver2.6.0 PB: SqliteSaver + live pubmed tool + 라우팅`

### Phase C — API + UI (tool 호출 노출)
- **C.1** `05_api/models.py`: `QueryResponse`에 `steps: list[dict]`(tool, query) 추가
  → verify: 스키마 import OK
- **C.2** `05_api/main.py`: `cached_chain`→`cached_agent`, `/chat`에 thread_id, `out["messages"]`에서 steps·pmids 추출, **수동 history 제거**
  → verify: curl 멀티턴(같은 session_id) + 응답 `steps` 포함
- **C.3** `06_ui/chat_interface.py`: tool 단계 `st.status`/expander 표시("🔧 search_pubmed_live('…')")
  → verify: 브라우저 `S1`·`S2`·`S3` + tool 호출 노출
- **C.4** `06_ui/sidebar.py`: 모델 옵션 `gemma4:26b`/`gemma4:31b`(gemma3:4b 제거)
  → verify: 모델 전환 동작
- **commit**: `ver2.6.0 PC: agent in API+UI + tool 노출`

### Phase D — 정리 + 품질 + 릴리스
- **D.1** `02_chain/rag_chain.py` 제거(대체됨); `get_chat_history` 이중주입 없음 grep 확인
  → verify: 어디서도 수동 history 미전달, 앱 정상
- **D.2** `gemma4:31b` 품질 확인
  → verify: `S1`-`S3` @ 31b
- **D.3** README 로드맵 `2.6.0 ✅` 표기 + `VERIFY.md`(S1-S3 결과·지연시간) 작성
- **D.4** dev 커밋 → main 머지 → **tag `v2.6.0`**

## 범위 제외

- 인증(2.4.0)·배포(2.5.0)
- 답변/사고 토큰 스트리밍 (tool trace는 완료 후 일괄 표시)
- 3번째 tool(`fetch_abstract_by_pmid` 등) — 필요해지면 추가
- 코퍼스 재구축·임베딩 변경, re-ranking/hybrid(검색 고도화는 별도)

## 리스크

- **멀티-tool 라우팅 신뢰도**: 단일 tool 루프는 검증됨. tool 2개에서 모델이 오라우팅하면
  시스템 프롬프트 튜닝 또는 `qwen3:32b` 교체. → 4단계에서 라우팅을 명시적으로 테스트.
- **`SqliteSaver` 스레드 안전성**: FastAPI 멀티스레드에서 connection 설정 주의
  (`check_same_thread=False` 등). 막히면 `MemorySaver`로 먼저 루프 완성 후 영속화 보강.
- **`search_pubmed_live` 지연·rate limit**: 네트워크 + NCBI 제한. retmax 소량, timeout,
  graceful 에러로 바운드.
- **모델 일관성**: dev(gemma4:26b)·quality(gemma4:31b) 동일 family라 거동 일치. qwen3로
  폴백 시 `<think>` 태그가 답변/UI에 새지 않게 후처리 필요.
- **chroma sqlite read-write 부작용**(기존 wart): 검색 tool이 chroma를 열면 `chroma.sqlite3`가
  modified 표시됨 → 실행 후 `git restore`, 커밋 금지(ver2.2.0과 동일).
- **`get_chat_history` 역할 변경**: 더 이상 체인 입력이 아님. API/CLI에서 수동 history 전달 코드를
  제거하지 않으면 history가 이중 주입될 수 있음 → 5·7단계에서 제거 확인.
