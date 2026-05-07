# 프로젝트 현황 분석

> 목표: PubMedBERT로 논문 데이터를 임베딩하고, LLM과 연결한 RAG 기반 ChatBot을 구현한다.

---

## 1. RAG ChatBot에 원론적으로 필요한 것

### A. 데이터 파이프라인
- [ ] 논문 수집 (PubMed API 등)
- [ ] 전처리 (HTML 정리, 결측치 제거, 필터링)
- [ ] 키워드 스크리닝

### B. 임베딩 & 벡터 DB
- [ ] 도메인 특화 임베딩 모델 (PubMedBERT)
- [ ] 벡터 DB 구축 및 저장 (ChromaDB 등)
- [ ] 유사도 검색 (Semantic Search)

### C. RAG 핵심
- [ ] Query Embedding (사용자 질문 → 벡터)
- [ ] Retriever (관련 논문 Top-K 검색)
- [ ] Context Assembly (검색 결과 → 프롬프트 조립)
- [ ] LLM 답변 생성 (검색 기반 근거 답변)

### D. 대화형 인터페이스
- [ ] 대화 기록 (Conversation History / Memory)
- [ ] 멀티턴 대화 (이전 문맥 유지)
- [ ] 스트리밍 응답
- [ ] Web UI 또는 풍부한 인터페이스
- [ ] Follow-up 질문 처리

### E. 품질 & 고도화
- [ ] Re-ranking (검색 결과 재정렬)
- [ ] Hybrid Search (키워드 + 시맨틱)
- [ ] 답변 출처 인용 (PMID 등)
- [ ] 평가 체계 (Retrieval 정확도, 답변 품질)

---

## 2. 현재 완료된 것 (90_RAG-Pipeline)

### A. 데이터 파이프라인 — ✅ 완료
- ✅ PubMed Entrez API로 논문 수집 (수산 부산물 바이오 활성 도메인)
- ✅ 3단계 전처리 (HTML 정리 → 결측치 제거 → 연도 필터)
- ✅ 3그룹 키워드 스크리닝 (Part × Category × Function)
- ✅ 최종 데이터: 5,590편 논문

### B. 임베딩 & 벡터 DB — ✅ 완료
- ✅ PubMedBERT (microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext)
- ✅ 768차원 임베딩, Attention-aware mean pooling
- ✅ ChromaDB (L2 distance, PersistentClient)
- ✅ 체크포인트 기반 임베딩 (중단 시 재개 가능)

### C. RAG 핵심 — ✅ 완료
- ✅ 질문 임베딩 → ChromaDB 시맨틱 검색 → Top-K 논문
- ✅ 프롬프트 조립 (System + Context + Question)
- ✅ Claude Haiku / Gemini Flash 이중 백엔드
- ✅ PMID 인용 강제 시스템 프롬프트

### D. 대화형 인터페이스 — ⚠️ 최소한만 구현
- ✅ CLI 인터페이스 (명령어: quit, k, papers, help)
- ✅ 자동 로깅 (Markdown)
- ❌ **대화 기록 없음 (Stateless — 매 질문이 독립적)**
- ❌ **멀티턴 대화 불가 (이전 문맥을 모름)**
- ❌ **스트리밍 응답 없음**
- ❌ **Web UI 없음**
- ❌ **Follow-up 질문 처리 불가**

### E. 품질 & 고도화 — ❌ 미구현
- ❌ Re-ranking 없음
- ❌ Hybrid Search 없음
- ❌ 평가 체계 없음

---

## 3. GAP 분석 — 지금 해야 할 것

| 우선순위 | 항목 | 현재 | 목표 | 난이도 |
|---------|------|------|------|--------|
| 🔴 P0 | 대화 기록 (Memory) | 없음 | 멀티턴 대화 지원 | 중 |
| 🔴 P0 | 멀티턴 문맥 유지 | 없음 | 이전 대화 참조 가능 | 중 |
| 🟡 P1 | 스트리밍 응답 | 없음 | 토큰 단위 실시간 출력 | 하 |
| 🟡 P1 | Web UI | CLI만 | Gradio/Streamlit 등 | 중 |
| 🟡 P1 | Re-ranking | 없음 | Cross-encoder 재정렬 | 중 |
| 🟢 P2 | Hybrid Search | 시맨틱만 | 키워드 + 시맨틱 결합 | 중 |
| 🟢 P2 | 평가 체계 | 없음 | Retrieval/답변 품질 측정 | 상 |

### 핵심 Gap 요약

**가장 큰 부재: "대화"가 없다.**

현재 챗봇은 Q&A 검색엔진에 가깝다. 질문마다 독립적으로 처리되어 "아까 말한 논문에서..." 같은 자연스러운 대화가 불가능하다. RAG 파이프라인 자체는 잘 갖춰져 있으므로, **Memory/History 계층을 추가하는 것이 최우선 과제**다.
