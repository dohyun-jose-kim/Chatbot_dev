# TODO List

---

## 1. 글루 코드 — 조각 연결

### Phase 1: 대화가 되게
- [ ] 우리 ChromaDB → LangChain retriever로 연결
- [ ] 우리 PubMedBERT → LangChain embedding으로 연결
- [ ] Claude API → LangChain LLM으로 연결
- [ ] LangChain `create_history_aware_retriever` 적용 (대화 메모리)
- [ ] LangChain `create_retrieval_chain` 적용 (RAG 체인)
- [ ] Streamlit session_state로 대화 기록 관리
- [ ] Claude API `stream=True` → Streamlit 스트리밍 연결

### Phase 2: 쓸 만하게
- [ ] Streamlit 챗봇 UI 구성 (chat_input, chat_message, 사이드바)
- [ ] CrossEncoder re-ranker → 검색 파이프라인에 연결
- [ ] (선택) EnsembleRetriever (BM25 + 시맨틱) 연결
- [ ] (선택) HyDE 쿼리 확장 연결

---

## 2. 프롬프트 — 우리 도메인 맞춤

- [ ] 멀티턴 system prompt 작성 (이전 대화 참조 지시 포함)
- [ ] 질문 재작성 prompt 작성 ("아까 그 논문" → 독립적 질문으로 변환)
- [ ] 답변 언어 설정 (한국어/영어 선택)
- [ ] 기존 프롬프트(`config.py`) 개선 (인용 규칙, 답변 구조)

---

## 3. 평가용 테스트 데이터

- [ ] 테스트 질문 세트 작성 (최소 20~30개)
  - 예: "키토산의 항산화 효과는?", "어류 콜라겐의 항염증 활성은?"
- [ ] 각 질문에 대한 기대 답변(ground truth) 작성
- [ ] 각 질문에 대한 기대 논문 목록(관련 PMID) 정리
- [ ] RAGAS 평가 스크립트 구성 (Medical-Chatbot-LLM-RAG 참고)
- [ ] 평가 실행 및 결과 기록
