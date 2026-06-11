# PubMed RAG Chatbot -- 수산부산물 기능성 논문 질의응답 시스템

PubMed 논문 5,590편을 PubMedBERT 임베딩 + ChromaDB로 검색하고, Claude Haiku API로 근거 기반 답변을 생성하는 CLI 챗봇.

---

## 디렉토리 구조

```
RAG_Pipeline/
├── config.py                  # 경로, 모델명, 프롬프트 등 중앙 설정
├── run_all.sh                 # 파이프라인 일괄 실행 (임베딩 -> DB -> 챗봇)
├── requirements.txt
├── data/
│   └── screened.csv           # 스크리닝된 논문 5,590편 (20MB)
├── 01_embedding/
│   └── embed.py               # PubMedBERT 임베딩 생성
├── 02_vectordb/
│   └── build_db.py            # ChromaDB 구축
├── 03_chatbot/
│   ├── chatbot.py             # CLI 메인 루프
│   ├── retriever.py           # ChromaDB 검색 + 쿼리 임베딩
│   └── llm.py                 # Claude/Gemini API 호출
├── outputs/                   # gitignored
│   ├── 01_embedding/
│   │   ├── embeddings.npy     # (5590, 768) 벡터
│   │   └── pmids.csv
│   └── 02_vectordb/
│       └── chroma_db/         # 벡터 DB
└── Docs/
    ├── total-act.md           # 파이프라인 상세 기록
    ├── 01_embedding.md        # 임베딩 모듈 문서
    ├── 02_vectordb.md         # 벡터DB 모듈 문서
    ├── 03_chatbot.md          # 챗봇 모듈 문서
    ├── overview-nontechnical.md  # 비전문가용 소개
    ├── requirements.md        # 환경 요구사항
    └── logs/                  # 테스트 로그
```

---

## 빠른 시작

### 1. 의존성 설치

```bash
source /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/.venv/bin/activate
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
echo "export ANTHROPIC_API_KEY='sk-ant-api03-...'" > ~/.anthropic_key
```

### 3. 파이프라인 실행

```bash
cd /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/week_7/RAG_Pipeline
bash run_all.sh
```

임베딩이 이미 생성되어 있으면 자동 스킵되며, ChromaDB 빌드 후 챗봇이 실행된다.

---

## 상세 문서

각 모듈의 상세 설명은 `Docs/` 디렉토리를 참조:

- [Docs/total-act.md](Docs/total-act.md) -- 전체 파이프라인 상세 기록
- [Docs/01_embedding.md](Docs/01_embedding.md) -- PubMedBERT 임베딩
- [Docs/02_vectordb.md](Docs/02_vectordb.md) -- ChromaDB 벡터 DB
- [Docs/03_chatbot.md](Docs/03_chatbot.md) -- 챗봇 모듈 (retriever, llm, cli)
- [Docs/overview-nontechnical.md](Docs/overview-nontechnical.md) -- 비전문가용 소개
- [Docs/requirements.md](Docs/requirements.md) -- 환경 및 설치 가이드
