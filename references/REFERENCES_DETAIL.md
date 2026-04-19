# 참고 프로젝트 상세 분석

---

## 1. Medical-RAG-LLM ⭐ 클론 추천

> [GitHub](https://github.com/AquibPy/Medical-RAG-LLM) — 우리와 가장 유사한 프로젝트

**구조:**
```
app.py                  ← FastAPI 웹 서버
create_vector_db.py     ← 벡터 DB 생성
settings.py             ← 설정
data/                   ← 의료 문서
templates/              ← HTML 프론트엔드
```

**스택:** PubMedBERT (임베딩) + BioMistral 7B (LLM) + Qdrant (벡터DB) + LangChain + FastAPI

**우리와의 차이점:**
| | 우리 | Medical-RAG-LLM |
|---|---|---|
| 임베딩 | PubMedBERT ✅ 동일 | PubMedBERT ✅ 동일 |
| LLM | Claude Haiku (API) | BioMistral 7B (로컬) |
| 벡터DB | ChromaDB | Qdrant |
| 서버 | 없음 (CLI) | FastAPI |
| 프레임워크 | 직접 구현 | LangChain |

**가져갈 것:** FastAPI 서버 구조, LangChain 통합 패턴

---

## 2. Medical-Chatbot-LLM-RAG ⭐ 클론 추천

> [GitHub](https://github.com/puja-urmi/Medical-Chatbot-LLM-RAG) — 평가 체계 참고

**RAGAS 평가 결과:**
| 메트릭 | 점수 |
|-------|------|
| Context Precision | 96.7% |
| Context Recall | 95.0% |
| Faithfulness | 85.0% |
| Answer Relevancy | 73.0% |
| Answer Correctness | 69.4% |

**구조:** Jupyter Notebook 기반
1. 데이터 임포트 → 2. 벡터DB 생성 → 3. 검증 쿼리 테스트 → 4. RAG 파이프라인 → 5. RAGAS 평가

**가져갈 것:** RAGAS 평가 프레임워크 — 우리 챗봇의 성능을 정량적으로 측정할 수 있는 방법론

---

## 3. MedRAG

> [GitHub](https://github.com/Teddy-XiongGZ/MedRAG) — 벤치마크 / 연구 참고

**규모:** 7,663개 의료 질문, 1.8조 프롬프트 토큰, 41가지 조합 테스트

**테스트한 코퍼스:**
- PubMed (23.9M 초록), StatPearls (9.3K), Textbooks (18권), Wikipedia (6.5M)

**테스트한 리트리버:**
- BM25 (키워드) / Contriever (범용 시맨틱) / SPECTER (학술) / MedCPT (바이오메디컬)

**핵심 발견:** RAG 적용 시 GPT-3.5도 GPT-4 수준까지 올라감 (+18%)

**가져갈 것:** 리트리버 선택 근거. 우리가 PubMedBERT만 쓰는 게 최선인지 판단할 때 참고. 클론보다는 논문 읽기가 더 유용.

---

## 4. conversational-rag-chatbot ⭐ 클론 추천

> [GitHub](https://github.com/aryanmahawar205/conversational-rag-chatbot) — Phase 1 직접 참고

**메모리 구현 방식:**
- SQLite에 session_id별 대화 기록 저장
- follow-up 질문 시 같은 세션의 이전 메시지를 가져와서 문맥 유지

**구조:**
```
/api                    ← FastAPI 백엔드
  ├─ db_utils.py        ← 대화 기록 DB 관리
  ├─ langchain_utils.py ← RAG 파이프라인
  └─ chroma 관련
/app                    ← Streamlit 프론트엔드
  ├─ chat 화면
  └─ 파일 업로드 사이드바
```

**스택:** FastAPI + Streamlit + ChromaDB + LangChain + OpenAI

**가져갈 것:**
1. `db_utils.py` — session 기반 대화 저장 패턴
2. `langchain_utils.py` — 메모리 포함 RAG 파이프라인
3. FastAPI + Streamlit 분리 구조

---

## 5. Kotaemon

> [GitHub](https://github.com/Cinnamon/kotaemon) — Phase 2 UI + 고급 RAG 참고

**핵심 특징:**
- Gradio 기반 UI (커스텀 테마 패키지 포함)
- **Hybrid RAG**: full-text + vector 검색 + re-ranking
- 멀티 문서 동시 Q&A
- 인용 표시 + PDF 미리보기 + 신뢰도 낮을 때 경고
- LLM: OpenAI / Azure / Ollama 지원
- 벡터DB: Elasticsearch / LanceDB / ChromaDB

**가져갈 것:** Gradio 챗봇 UI 구현 패턴, hybrid retrieval 설계. 다만 프로젝트가 매우 크므로 클론보다는 특정 파일만 참고.

---

## 6. DeepSeek-RAG-Chatbot

> [GitHub](https://github.com/SaiAkhil066/DeepSeek-RAG-Chatbot) — 고급 검색 참고

**"Ultimate RAG Stack" 구성:**
1. **Hybrid Search** — BM25 (키워드) + FAISS (시맨틱) 병합
2. **HyDE** — 질문으로 가상 답변을 생성 → 그걸로 검색 (recall 향상)
3. **Cross-Encoder Re-ranking** — 검색 결과를 재정렬
4. **GraphRAG** — 문서에서 지식 그래프 추출
5. **Chat Memory** — 대화 기록 유지

**가져갈 것:** Phase 3에서 검색 고도화할 때 HyDE, hybrid search, re-ranking 구현 참고. 완전 로컬(오프라인)이라 API 없이도 동작.

---

## 클론 추천 요약

| 프로젝트 | 클론? | 이유 |
|---------|-------|------|
| **Medical-RAG-LLM** | ✅ 클론 | PubMedBERT 동일, FastAPI 구조 참고 |
| **Medical-Chatbot-LLM-RAG** | ✅ 클론 | RAGAS 평가 코드 참고 |
| **conversational-rag-chatbot** | ✅ 클론 | Phase 1 메모리 구현 직접 참고 |
| MedRAG | ❌ 논문만 | 벤치마크 데이터, 클론할 필요 없음 |
| Kotaemon | ❌ 부분 참고 | 너무 큼, 필요할 때 특정 파일만 보기 |
| **DeepSeek-RAG-Chatbot** | ✅ 클론 | Phase 3 고급 검색 참고 (HyDE, hybrid, re-ranking) |
