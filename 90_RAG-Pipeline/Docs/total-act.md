임베딩 

 pubmed bert

chroma db 에 메타데이터 첨부 

이 다음부터 챗봇의 영역
---
 사용자: "antioxidant activity of fish collagen peptide"                                                                      
            │                                                                                                                  
            ▼ ① retriever.py                                                                                                   
    PubMedBERT가 질문을 768차원 벡터로 변환 (로컬, 무료)                                                                       
            │                                                                                                                  
            ▼ ② ChromaDB 검색                                                                                                  
    5,590편 중 가장 유사한 논문 5편 검색 (로컬, 무료)                                                                          
            │                                                                                                                  
            ▼ ③ llm.py — 여기서 돈 나감                                                                                        
    Claude Haiku에게 보내는 것:                                                                                                
      - 시스템 프롬프트 (역할 지시, ~100 토큰)                                                                                 
      - 논문 5편의 초록 텍스트 (~3,000~5,000 토큰)                                                                             
      - 질문 (~20 토큰)                                                                                                        
                                                                                                                               
    Claude가 보내주는 것:                                                                                                      
      - PMID 인용 포함 답변 (~300~500 토큰)                                                                                    
            │                                                                                                                  
            ▼                                                                                                                  
    터미널에 답변 출력                                                                                                         
                                                                                                                               
  비용: 질문 1회당 약 $0.003 (0.3센트)                                                                                         
                                                                                                                               
  $5 충전했으면 ~1,500번 질문 가능합니다. 테스트 1번 돌려볼까요? 

---
## 실행 방법 메모

처음에 `ANTHROPIC_API_KEY`가 터미널 세션에 안 잡혀서 `[Error] Invalid API key` 발생.

이렇게 하니까 되더라:
```bash
source ~/.anthropic_key && PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 \
  /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/.venv/bin/python3 03_chatbot/chatbot.py \
  2>&1 | tee Docs/logs/test2.md
```

그래서 `run_all.sh`에 API 키 로드 + MPS 메모리 설정 + tokenizer 경고 억제를 전부 넣어둠.

**최종 실행 명령:**
```bash
cd /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/week_7/RAG_Pipeline
bash run_all.sh
```
이것만 하면 임베딩(이미 있으면 스킵) → ChromaDB 빌드 → 챗봇 실행까지 전부 자동.

---

## 전체 파이프라인 흐름도

```
screened.csv (5,590편, 20MB)
    │
    ▼ ① embed.py (01_embedding/)
    │  PubMedBERT로 각 논문 초록을 768차원 벡터로 변환
    │  - Tokenize → Transformer forward pass → Mean pooling
    │  - 배치 단위(32) 처리, 체크포인트(50배치마다) 저장
    │  - MPS 가속 사용, PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
    │
    ├→ embeddings.npy  (5590 x 768, ~34MB)
    ├→ pmids.csv       (5590행)
    │
    ▼ ② build_db.py (02_vectordb/)
    │  ChromaDB에 벡터 + 메타데이터 적재
    │  - 벡터: PubMedBERT 768차원 임베딩
    │  - 문서: 초록 원문
    │  - 메타: pmid, title, year, journal, mesh_terms
    │  - 배치 500건씩 upsert
    │
    ├→ chroma_db/      (outputs/02_vectordb/chroma_db/)
    │
    ▼ ③ chatbot.py (03_chatbot/)
    │
    │  사용자 질문
    │      │
    │      ▼ retriever.py
    │  PubMedBERT가 질문을 768차원 벡터로 변환 (로컬, 무료)
    │      │
    │      ▼ ChromaDB 검색
    │  5,590편 중 가장 유사한 논문 Top-K편 검색 (로컬, 무료)
    │      │
    │      ▼ llm.py
    │  Claude Haiku에게 시스템 프롬프트 + 논문 초록 + 질문 전송
    │      │
    │      ▼
    │  PMID 인용 포함 답변 출력
```

---

## 단계별 입출력 상세

### Step 1: 임베딩 생성 (01_embedding/embed.py)

| 항목 | 내용 |
|------|------|
| 입력 | `data/screened.csv` (abstract 컬럼) |
| 출력 | `outputs/01_embedding/embeddings.npy` (5590 x 768) |
| 출력 | `outputs/01_embedding/pmids.csv` (5590행) |
| 모델 | `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` |
| 배치 | 32건, 최대 토큰 길이 512 |
| 체크포인트 | `outputs/01_embedding/checkpoints/chunk_NNNN.npy` (50배치마다) |

### Step 2: 벡터DB 구축 (02_vectordb/build_db.py)

| 항목 | 내용 |
|------|------|
| 입력 | `outputs/01_embedding/embeddings.npy` + `pmids.csv` + `data/screened.csv` |
| 출력 | `outputs/02_vectordb/chroma_db/` (영구 저장) |
| 컬렉션명 | `pubmed_abstracts` |
| 배치 | 500건씩 add |
| 검증 | 빌드 후 자동으로 첫 번째 문서 기준 유사 검색 수행 |

### Step 3: 챗봇 (03_chatbot/)

| 항목 | 내용 |
|------|------|
| 입력 | 사용자 질문 (영어) |
| 처리 | retriever.py -> llm.py -> 터미널 출력 |
| LLM | Claude Haiku (claude-haiku-4-5-20251001), 최대 1024 토큰 |
| 폴백 | Gemini 2.0 Flash (config.py에서 LLM_BACKEND 변경) |

---

## Shard 임베딩 방식 설명

초기 시도에서 5,590편 전체를 한번에 임베딩하려 했으나, Intel Mac의 MPS 메모리 제한으로 중간에 프로세스가 종료되는 문제가 있었다.

이를 해결하기 위해 screened.csv를 3개 샤드로 분할하여 순차 처리하는 방식을 도입했다:

```bash
python 01_embedding/embed.py data/screened_1of3.csv
python 01_embedding/embed.py data/screened_2of3.csv
python 01_embedding/embed.py data/screened_3of3.csv
```

각 샤드는 `embeddings_1of3.npy`, `embeddings_2of3.npy`, `embeddings_3of3.npy`로 저장되며, 이후 병합하여 최종 `embeddings.npy`를 생성한다.

`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` 환경변수를 설정하면 MPS 메모리 워터마크를 해제하여 메모리 부족 문제를 완화할 수 있다. 이 설정 이후에는 전체 데이터를 샤드 없이 처리할 수 있었다.

---

## PMID 순서 문제 (Round-Robin Split)

샤드 분할 시 round-robin 방식으로 행을 나누면, 각 샤드의 PMID 순서가 원본 CSV와 달라진다. 예를 들어:

```
원본: [P1, P2, P3, P4, P5, P6]
1of3: [P1, P4]
2of3: [P2, P5]
3of3: [P3, P6]
병합: [P1, P4, P2, P5, P3, P6]  -- 원본과 순서 불일치
```

이 경우 `build_db.py`에서 screened.csv의 메타데이터와 embeddings.npy의 행 순서가 맞지 않아 잘못된 벡터가 논문에 매핑된다.

해결 방법: `pmids.csv`를 기준으로 순서를 맞추도록 `build_db.py`에서 PMID set 기반 필터링을 수행한다. 최종적으로 `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` 설정 후 전체 데이터를 한번에 처리하여 이 문제를 근본적으로 회피했다.

---

## 성능 수치

테스트 환경: Intel Mac, MPS 가속, Python 3.12.12

| 단계 | 소요 시간 | 비고 |
|------|----------|------|
| 임베딩 생성 (5,590편) | 약 60~90분 | MPS, batch_size=32 |
| ChromaDB 빌드 | 약 1~2분 | batch_size=500 |
| 검색 (쿼리 1건) | 약 1.2초 | PubMedBERT 쿼리 임베딩 + ChromaDB 검색 |
| LLM 답변 생성 | 약 4~7초 | Claude Haiku, 네트워크 지연 포함 |
| 총 질문-답변 | 약 5~8초 | 검색 + 생성 합산 |

비용: 질문 1회당 약 $0.003 (0.3센트). $5 충전 시 약 1,500번 질문 가능.