# first look

PubMed 논문 5,590편 → PubMedBERT → ChromaDB → Claude/Gemini 듀얼 백엔드 RAG. 엔드투엔드 동작. 수준: 석사과정~주니어 실무. 임베딩-검색 pooling 일치성, 체크포인트 재개 등 RAG의 함정을 이해한 코드. 약점: 이름이 "Chatbot"인데 대화 기억 없는 stateless Q&A. (STATUS.md에 본인이 이미 인지.) 정량 평가(RAGAS) 없음. 코칭: 둘 중 하나를 골라라 — (a) "Domain RAG Search Engine"으로 개명하고 완성 선언, (b) Phase 1(멀티턴+UI)을 구현해 이름값. 어중간하게 두는 것이 최악. 발전 가능성은 9개 중 최고 (바이오 도메인 차별화).

# ver1
/Users/inco/01_Projects/dohyun-jose-kim/03_Chatbot-RAG-LLM/90_RAG-Pipeline 은 ver1 로 규정하고 "Domain RAG Search Engine"

# ver2.0.0
## ver2.1.0 ==  멀티턴
## ver2.2.0 == UI
## ver2.3.0 == app
## ver2.4.0 == user config, id, pw
## ver2.5.0 == server deploy