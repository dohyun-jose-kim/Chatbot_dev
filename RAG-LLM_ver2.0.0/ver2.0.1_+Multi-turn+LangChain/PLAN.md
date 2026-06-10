# ver2.0.1 — Multi-turn + LangChain 구현 계획

> 참고: for2-0-0-KiskStart.md 에는 멀티턴이 "ver2.1.0"으로 적혀 있음.
> 본 디렉터리명(ver2.0.1)을 기준으로 진행. 필요시 KickStart 문서 갱신.

## 목표

ver1(90_RAG-Pipeline)의 stateless Q&A를 **멀티턴 대화형 RAG**로 전환.

- LLM: Claude/Gemini API → **로컬 Ollama** (`gemma4:31b`, 개발 중엔 `gemma3:4b`)
- 프레임워크: 직접 구현 → **LangChain** (챗봇 레이어만)
- 데이터: ver1의 chroma_db(PubMed 5,590편, PubMedBERT 임베딩)를 **읽기 전용으로 재사용**. 수집~DB구축 파이프라인(00~02)은 손대지 않음.

**성공 기준 (검증 시나리오)**
```
Q1: "What bioactivities does fish scale collagen have?"
Q2: "What about its antioxidant effects?"   ← 대명사 "its" 사용
```
Q2에서 (a) 질문이 standalone으로 재작성되어 collagen 관련 논문이 검색되고,
(b) 답변이 PMID 인용 형식을 유지하면 성공.

## 빌려오는 것 (직접 구현 최소화)

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| references/conversational-rag-chatbot `langchain_utils.py` | 멀티턴 체인 구조 (`create_history_aware_retriever` + `create_retrieval_chain`), contextualize 프롬프트 | `ChatOpenAI` → `ChatOllama`, import는 `langchain.chains` → `langchain_classic.chains` (LangChain 1.x에서 레거시 체인 분리됨) |
| references/conversational-rag-chatbot `db_utils.py` | 세션별 대화기록 SQLite 저장/복원 | document_store 관련 함수 제거 (문서 업로드 기능 안 씀) |
| ver1 `03_chatbot/retriever.py` | PubMedBERT 임베딩 + mean_pooling + chroma 검색 로직 | LangChain `BaseRetriever` 인터페이스로 감싸기 |
| ver1 `config.py` | 프롬프트(SYSTEM_PROMPT, CONTEXT_TEMPLATE), 경로, TOP_K | LLM 섹션을 Ollama용으로 교체 |
| ver1 `03_chatbot/chatbot.py` | CLI 루프 UX (`k`, `papers`, `help` 명령) | `new`(새 세션) 명령 추가 |

## 핵심 설계 결정

### 1. Retriever: `langchain_chroma.Chroma` 대신 커스텀 `BaseRetriever`

표준 방법은 PubMedBERT를 LangChain `Embeddings`로 감싸고 `langchain_chroma.Chroma`로
기존 DB를 여는 것. 하지만 ver1은 **PMID를 chroma의 id로 저장**했고(metadata 아님),
LangChain Chroma 래퍼의 Document에서는 id 접근이 번거로워 PMID 인용이 깨진다.

→ ver1 `retriever.py`의 검색 로직을 거의 그대로 쓰면서 `BaseRetriever`만 구현 (~40줄).
검색 결과를 `Document(page_content=abstract, metadata={pmid, title, year, journal, distance})`로
반환하면 PMID가 metadata에 안전하게 들어간다.

### 2. 컨텍스트 포맷: `create_stuff_documents_chain`의 `document_prompt` 활용

ver1의 CONTEXT_TEMPLATE(PMID/연도/저널/제목 포함)을 LangChain `PromptTemplate`으로 변환해
`document_prompt` 파라미터로 주입. 별도 포맷팅 코드 불필요.

### 3. 모델 전략

```python
LLM_MODEL = "gemma4:31b"   # 품질 확인용
DEV_MODEL = "gemma3:4b"    # 개발/디버깅용 (멀티턴은 턴당 LLM 2회 호출이라 느림)
```
`chat.py --dev` 플래그 또는 환경변수로 전환.

### 4. 대화기록: SQLite (레퍼런스 레포 방식 그대로)

- `chat_history.db`, 테이블 `application_logs(session_id, user_query, response, model, created_at)`
- 세션 시작 시 uuid 발급, `new` 명령으로 세션 리셋
- 매 턴: 기록 조회 → 체인에 `chat_history` 주입 → 응답 후 저장

## 파일 구성

```
ver2.0.1_+Multi-turn+LangChain/
├── PLAN.md                    # 이 문서
├── config.py                  # 경로(ver1 chroma_db 절대경로), 모델명, TOP_K, 프롬프트
├── pubmedbert_retriever.py    # ver1 retriever → LangChain BaseRetriever 어댑터 (~80줄)
├── rag_chain.py               # 멀티턴 체인 조립: ChatOllama + history-aware retriever (~50줄)
├── db_utils.py                # 세션별 대화기록 SQLite (~50줄, 레퍼런스 차용)
├── chat.py                    # CLI 멀티턴 루프 (~100줄, ver1 chatbot.py 차용)
└── requirements.txt           # langchain, langchain-classic, langchain-ollama, chromadb, torch, transformers
```

ver1 디렉터리는 import하지 않고 필요한 코드를 복사해온다 (ver1 동결 원칙, sys.path 꼬임 방지).

## 구현 순서 (각 단계 검증 포함)

```
1. config.py + requirements.txt + venv 셋업
   → verify: ollama에 gemma3:4b로 ChatOllama 단발 호출 성공

2. pubmedbert_retriever.py
   → verify: 테스트 질의로 ver1 retriever.py와 동일한 PMID top-5 반환

3. rag_chain.py (단일턴 먼저)
   → verify: chat_history=[] 로 invoke → PMID 인용 포함 답변 생성

4. db_utils.py + chat.py (멀티턴 완성)
   → verify: 성공 기준 시나리오(Q1→Q2 대명사 추적) 통과 @ gemma3:4b

5. gemma4:31b로 품질 확인
   → verify: 동일 시나리오 + 답변 품질/인용 정확성 육안 확인, 턴당 소요시간 기록

6. dev 브랜치 커밋
```

## 범위 제외 (이번 버전에서 안 함)

- UI (ver2.2.0), FastAPI 서버 (ver2.3.0), 사용자 인증 (ver2.4.0)
- RAGAS 등 정량 평가 (별도 버전에서)
- chroma_db 재구축, 임베딩 변경
- qwen3 지원 (`<think>` 태그 후처리 필요 → 필요해지면 그때)

## 리스크

- **gemma4:31b 응답 속도**: 턴당 2회 호출 × 19GB 모델. 너무 느리면 질문 재작성만
  gemma3:4b로 분리하는 2-모델 구성 고려 (체인에서 LLM을 단계별로 다르게 주입 가능).
- **chromadb 버전 호환**: ver1 DB는 chromadb>=1.0으로 빌드됨. ver2 venv도 같은 메이저 버전 고정.
- **contextualize 품질**: 작은 모델이 질문 재작성을 망치면 검색이 엉뚱해짐.
  검증 단계에서 재작성된 질문을 로그로 찍어 확인.
