# PubMed RAG Chatbot -- Compact Portable Package

PubMed 논문 5,590편을 PubMedBERT 임베딩 + ChromaDB로 검색하고, Claude Haiku API로 근거 기반 답변을 생성하는 RAG 챗봇.
기존 데이터 포함 + 새 도메인 적용을 위한 풀 파이프라인 포함.

---

## 디렉토리 구조

```
compact-RAG-Chatbot/
│
│  ── 데이터 수집 파이프라인 (새 도메인 적용 시 사용) ──
├── 00_collect/
│   └── collect_pubmed.py          # PubMed Entrez API 논문 수집 (v3 쿼리)
├── 00_preprocess/
│   ├── preprocess_step1.py        # HTML entity, 특수공백, 섹션라벨 제거
│   ├── preprocess_step2_deleteNANs.py  # abstract 결측치 제거
│   └── preprocess_step3_year_filter.py # 연도 필터 (2000년 이후)
├── 00_screening/
│   └── keyword_screen.py          # 3그룹 키워드 필터링 → data/screened.csv
│
│  ── 핵심 RAG 파이프라인 ──
├── config.py                      # 경로, 모델명, 프롬프트 등 중앙 설정
├── run_all.sh                     # 파이프라인 일괄 실행 (임베딩 → DB → 챗봇)
├── requirements.txt
├── 01_embedding/
│   └── embed.py                   # PubMedBERT 임베딩 생성 (체크포인트 지원)
├── 02_vectordb/
│   └── build_db.py                # ChromaDB 구축
├── 03_chatbot/
│   ├── chatbot.py                 # CLI 메인 루프
│   ├── retriever.py               # ChromaDB 검색 + 쿼리 임베딩
│   └── llm.py                     # Claude/Gemini API 호출
│
│  ── 데이터 ──
├── data/
│   └── screened.csv               # 스크리닝된 논문 5,590편 (20MB)
├── outputs/
│   ├── 01_embedding/
│   │   ├── embeddings.npy         # (5590, 768) 벡터 (~34MB)
│   │   └── pmids.csv
│   └── 02_vectordb/
│       └── chroma_db/             # 벡터 DB (~100MB)
│
│  ── 문서 ──
└── Docs/
    ├── overview-technical.md      # 아키텍처, 설계 결정, 성능 분석
    ├── overview-nontechnical.md   # 비전문가용 소개
    ├── total-act.md               # 파이프라인 상세 기록
    ├── 01_embedding.md
    ├── 02_vectordb.md
    ├── 03_chatbot.md
    └── requirements.md
```

---

## 빠른 시작 (기존 데이터로 바로 실행)

```bash
# 1. 가상환경 생성 + 의존성 설치
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. API 키 설정
export ANTHROPIC_API_KEY='sk-ant-...'

# 3. 실행 (임베딩/DB 이미 포함되어 있으므로 바로 챗봇 시작)
bash run_all.sh
```

---

## 새 도메인 적용 (풀 파이프라인)

```bash
# Step 0a: PubMed에서 논문 수집 (쿼리 수정 필요)
python 00_collect/collect_pubmed.py

# Step 0b: 전처리
python 00_preprocess/preprocess_step1.py
python 00_preprocess/preprocess_step2_deleteNANs.py
python 00_preprocess/preprocess_step3_year_filter.py

# Step 0c: 키워드 스크리닝 (키워드 수정 필요) → data/screened.csv 생성
python 00_screening/keyword_screen.py

# Step 1~3: 임베딩 → DB → 챗봇 (기존 outputs 삭제 후)
rm -rf outputs/
bash run_all.sh
```

---

## 기술 스택

| 구성요소 | 기술 |
|---------|------|
| Embedding | PubMedBERT (`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`) |
| Vector DB | ChromaDB (PersistentClient, L2 distance) |
| LLM | Claude Haiku 4.5 (기본) / Gemini 2.0 Flash (폴백) |
| Pooling | Attention-aware Mean Pooling (768-dim) |

상세 기술 문서: [Docs/overview-technical.md](Docs/overview-technical.md)
