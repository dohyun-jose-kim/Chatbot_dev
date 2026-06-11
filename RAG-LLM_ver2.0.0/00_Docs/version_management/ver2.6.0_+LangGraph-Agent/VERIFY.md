# ver2.6.0 검증 결과

고정 체인 → LangGraph tool-calling 에이전트(2 tool: `search_local_corpus` + `search_pubmed_live`).
성공 기준: S1(로컬 RAG) · S2(라이브 라우팅) · S3(멀티턴 대명사) + tool 호출 노출.

## 사전 검증 — 모델 tool-calling 지원

| 모델 | bind_tools | 비고 |
|---|---|---|
| `gemma4:31b` (quality) | ✅ | tool 호출 10.7s |
| `gemma4:26b` (dev) | ✅ | tool 호출 5.1s |
| `qwen3:14b` / `qwen3:32b` | ✅ | 대안(reasoning `<think>` 후처리 필요) |
| `gemma3:4b` (구 dev) | ❌ | Ollama 400 "does not support tools" → **dev 모델 교체** |
| `exaone3.5:32b` | ❌ | tool 미지원 |

`create_agent`(stub tool, gemma4:26b) 전체 ReAct 루프: 질문→tool→결과→답변 **5.5s** (4 messages).
import: LangChain v1 `langchain.agents.create_agent` (구 `langgraph.prebuilt.create_react_agent` deprecated).

## tool 단위 검증

| tool | 질의 | 결과 |
|---|---|---|
| `search_local_corpus` | "chitosan antimicrobial ... shrimp shells" | 코퍼스 PMID 5건 (37295482, 28923565, 29874447, 29800672, 41419504) |
| `search_pubmed_live` | "fish collagen peptide antioxidant" | 코퍼스 밖 최신 PMID (42270250 등) · 네트워크 에러 시 graceful |

## 에이전트 end-to-end (gemma4:26b, dev)

| 시나리오 | 라우팅된 tool (쿼리) | 인용 PMID | 시간 |
|---|---|---|---|
| **S1** 로컬 | `search_local_corpus('shrimp shell chitosan antimicrobial activity')` | 37295482, 28923565, 29874447, 22361180, 41419504 | 26.3s* |
| **S3** 멀티턴 "its" | `search_local_corpus('shrimp shell chitosan antioxidant activity')` ← 'its'=chitosan 해소 | 28923565, 38286562, 29874447, 21699985 | 14.1s |
| **S2** 라이브 | `search_pubmed_live('fish bone collagen peptides 2024 2025')` | 39581084 (최신) | 11.6s |

*S1은 PubMedBERT 첫 로드 포함. 세 시나리오 모두 적절한 tool 선택 + PMID 인용 + (S3) 대명사 해소.

## 품질 모델 (gemma4:31b)

S1 동일 질의 → `search_local_corpus` 라우팅, PMID 5건 인용, 근거 기반 답변. **86.9s** (로드 포함).
→ 개발은 gemma4:26b, 품질 확인만 31b 라는 2-모델 전략 유지(2.0.1과 동일 결론).

## API / CLI / UI

- **API**(`05_api`): `/chat` 라우트, `QueryResponse`에 `steps`·`pmids`, 기본 모델 `gemma4:26b`,
  `cached_agent`(모델별 1회 로드) 임포트·스키마 검증 통과. 에이전트 호출 경로는 위 e2e와 동일.
- **CLI**(`04_interface/chat.py`) / **UI**(`06_ui`): 전 파일 컴파일 통과, 에이전트로 전환,
  tool 단계 노출 배선 완료.
- ⏳ **수동 잔여**: 실서버(`./run_app.sh`) 브라우저 스모크(말풍선 누적·🔧 도구 호출 expander·모델 전환).
  에이전트/HTTP 스키마는 검증됨 — 브라우저 렌더만 미실행.

## 메모리

`SqliteSaver`(thread_id=session_id) 체크포인터로 멀티턴 유지(S3 통과). 질문 재작성 체인 불필요
(에이전트가 대화기록으로 tool 쿼리 형성). `application_logs`는 로깅용으로 유지.

## 결론

ver2.6.0 목표(RAG를 tool로 편입 + 멀티-tool 오케스트레이션) 달성. S1·S2·S3 통과, tool 노출 배선 완료.
브라우저 스모크만 수동 확인 후 `tag v2.6.0` 권장.

알려진 wart: chroma 조회 시 `chroma.sqlite3`가 read-write로 열려 modified 표시 → 실행 후
`git restore`, 커밋 금지(2.2.0과 동일).
