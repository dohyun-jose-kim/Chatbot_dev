# 참고 프로젝트: RAG-LLM Chatbot 오픈소스

---

## 🔬 우리 프로젝트와 가장 관련 높은 것 (바이오메디컬 RAG)

| 프로젝트 | 링크 | 핵심 | 참고 포인트 |
|---------|------|------|-----------|
| **MedRAG** | [GitHub](https://github.com/Teddy-XiongGZ/MedRAG) | 의료 RAG 벤치마크 (41가지 조합 테스트) | PubMed/StatPearls 코퍼스, BM25+SPECTER+MedCPT 리트리버, **평가 체계(MIRAGE)** |
| **Medical-RAG-LLM** | [GitHub](https://github.com/AquibPy/Medical-RAG-LLM) | PubMedBERT + BioMistral 7B | **우리와 같은 PubMedBERT 임베딩** 사용, Qdrant DB, 완전 오픈소스 |
| **Medical-RAG** | [GitHub](https://github.com/fenil210/Medical-RAG) | PubMed-BERT + BioMistral-7B 파인튜닝 | Semantic chunking, 환자 맞춤형 |
| **Medical-Chatbot-LLM-RAG** | [GitHub](https://github.com/puja-urmi/Medical-Chatbot-LLM-RAG) | PubMed 데이터 + RAGAS 평가 | **정확도 96.7%, 재현율 95%** — 평가 방법론 참고 |
| **Medical-Graph-RAG** | [GitHub](https://github.com/SuperMedIntel/Medical-Graph-RAG) | 지식 그래프 기반 의료 RAG (ACL 2025) | 고급 접근법, 논문 수준 |
| **PubMed RAG Screener** | [GitHub](https://github.com/milieere/pubmed-rag-screener) | PubMed 논문 스크리닝 + Streamlit | **Streamlit UI 구현 참고** |

---

## 🧠 대화 메모리 구현 참고 (우리의 P0 과제)

| 프로젝트 | 링크 | 메모리 방식 | 참고 포인트 |
|---------|------|-----------|-----------|
| **conversational-rag-chatbot** | [GitHub](https://github.com/aryanmahawar205/conversational-rag-chatbot) | 대화 메모리 + follow-up | FastAPI+Streamlit+ChromaDB — **우리 스택과 유사** |
| **RAG-with-Memory** | [GitHub](https://github.com/JINO-ROHIT/RAG-with-Memory) | Summary Memory (대화 요약) | 이전 대화를 요약해서 context로 활용 |
| **DeepSeek-RAG-Chatbot** | [GitHub](https://github.com/SaiAkhil066/DeepSeek-RAG-Chatbot) | Chat history + Hybrid 검색 | BM25+FAISS 하이브리드, 리랭킹, HyDE |
| **rag-chatbot (umbertogriffo)** | [GitHub](https://github.com/umbertogriffo/rag-chatbot) | Memory builder + React UI | ChromaDB 사용, FastAPI 백엔드 |

---

## 🏗️ 대규모 프레임워크 (아키텍처 참고) **참고**

| 프로젝트 | Stars | 핵심 | 언제 참고할까 |
|---------|-------|------|-------------|
| **LangChain** | ~134k | RAG 프레임워크의 표준 | Memory 모듈, ConversationBufferMemory 등 구현 패턴 |
| **LlamaIndex** | ~48k | 데이터 연결 프레임워크 | 인덱싱, 쿼리 엔진 설계 |
| **Haystack** | ~21k | 모듈러 파이프라인 | InMemoryChatMessageStore — 대화 저장 패턴 |

---

## 🖥️ UI 구현 참고

| 프로젝트 | Stars | UI | 참고 포인트 |
|---------|-------|-----|-----------|
| **Open WebUI** | ~133k | ChatGPT 스타일 웹 UI | RAG 내장, 문서 업로드, 멀티유저 |
| **Kotaemon** | ~25k | Gradio 기반 | **Gradio ChatInterface** — 우리 UI 후보와 동일 |
| **Verba** | ~7.2k | React | Weaviate 기반 올인원 RAG UI |

---

## 📚 큐레이션 리스트 **참고**

- [Awesome-RAG](https://github.com/Danielskry/Awesome-RAG) — RAG 프로젝트 모음
- [RAGHub](https://github.com/Andrew-Jang/RAGHub) — 커뮤니티 기반 RAG 리소스 모음

---

## 💡 우리 프로젝트에 가져갈 인사이트 **참고**

1. **Medical-RAG-LLM** → 우리와 같은 PubMedBERT 사용. Qdrant 대신 ChromaDB 쓰는 차이만 있음. 코드 구조 비교 가치 있음
2. **Medical-Chatbot-LLM-RAG** → RAGAS 평가 프레임워크로 정량 평가. 우리 평가 체계(P2) 구축 시 참고
3. **MedRAG** → 41가지 리트리버×코퍼스×LLM 조합 벤치마크. 우리 검색 품질 개선 방향 판단에 유용
4. **conversational-rag-chatbot** → ChromaDB + 대화 메모리. Phase 1 구현 시 직접 참고
5. **Kotaemon** → Gradio UI + Hybrid RAG + Re-ranking. Phase 2 UI 구현 시 참고
6. **DeepSeek-RAG-Chatbot** → Hybrid 검색(BM25+FAISS) + HyDE + 리랭킹. 고급 검색 구현 시 참고
