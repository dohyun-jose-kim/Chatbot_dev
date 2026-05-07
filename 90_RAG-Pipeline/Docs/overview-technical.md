# RAG Pipeline 기술 개요 (Technical Overview)

> 수산부산물 기능성 PubMed 논문 5,590편 기반 Retrieval-Augmented Generation 시스템
> 작성일: 2026-04-06

---

## 목차

1. [시스템 아키텍처](#1-시스템-아키텍처)
2. [설계 결정과 근거](#2-설계-결정과-근거)
3. [데이터 흐름과 텐서 변환](#3-데이터-흐름과-텐서-변환)
4. [벡터 공간과 검색 분석](#4-벡터-공간과-검색-분석)
5. [Prompt Engineering](#5-prompt-engineering)
6. [오류 처리와 복원력](#6-오류-처리와-복원력)
7. [성능 특성](#7-성능-특성)
8. [한계와 알려진 문제](#8-한계와-알려진-문제)
9. [향후 개선 방향](#9-향후-개선-방향)

---

## 1. 시스템 아키텍처

### 전체 구조

```
                          ┌──────────────────────────────────────────────┐
                          │           Offline Pipeline (1회 실행)         │
                          │                                              │
  screened.csv ──────────>│  embed.py ──> embeddings.npy + pmids.csv     │
  (5,590편, 11 cols)      │      │                                       │
                          │      v                                       │
                          │  build_db.py ──> ChromaDB (chroma_db/)       │
                          └──────────────────────────────────────────────┘
                                               │
                                               │ PersistentClient
                                               v
                          ┌──────────────────────────────────────────────┐
                          │           Online Pipeline (매 질문마다)       │
                          │                                              │
  User Query ────────────>│  Retriever                                   │
  (영어 텍스트)            │    │ PubMedBERT: query -> 768-dim vector     │
                          │    │ ChromaDB: L2 nearest neighbor search    │
                          │    v                                         │
                          │  Top-K papers (default K=5)                  │
                          │    │                                         │
                          │    v                                         │
                          │  LLM (Claude Haiku / Gemini Flash)           │
                          │    │ System prompt + Context + Question      │
                          │    v                                         │
                          │  Answer (PMID 인용 포함) ──────> Terminal     │
                          └──────────────────────────────────────────────┘
```

### 모듈 의존 관계

```
config.py  <──────────── 모든 모듈이 import
    │
    ├── 01_embedding/embed.py        (독립 실행)
    ├── 02_vectordb/build_db.py      (embed.py 출력에 의존)
    └── 03_chatbot/
            ├── retriever.py         (ChromaDB + PubMedBERT)
            ├── llm.py               (Claude / Gemini API)
            └── chatbot.py           (retriever + llm 조합)
```

`config.py`가 단일 진실 공급원(single source of truth)으로 기능한다. 경로, 모델명, 하이퍼파라미터, 프롬프트 템플릿이 모두 여기에 집중되어 있어, 설정 변경 시 한 파일만 수정하면 파이프라인 전체에 반영된다.

---

## 2. 설계 결정과 근거

### 2.1 Embedding Model: 왜 PubMedBERT인가

**선택한 모델**: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`

| 후보 | 장점 | 단점 | 탈락 이유 |
|------|------|------|----------|
| **PubMedBERT** (선택) | PubMed 전문/초록으로만 사전학습, 의생명 도메인 용어 이해도 최상 | 영어 전용, 768-dim 고정 | -- |
| `all-MiniLM-L6-v2` (sentence-transformers) | 빠름 (384-dim), 범용 유사도 최적화 | 일반 도메인 학습, "chitosan", "collagen peptide" 등 전문 용어 표현력 부족 | 도메인 특화 부족 |
| `BERT-base-uncased` | 가장 널리 사용, 참고 자료 풍부 | Wikipedia+BookCorpus 학습, 의생명 용어 OOV 비율 높음 | 도메인 특화 부족 |
| OpenAI `text-embedding-3-small` | 고품질, API 기반 간편 | 유료 (5,590편 임베딩 비용), 외부 의존성 | 비용, 로컬 실행 불가 |

핵심 논거: 이 시스템이 다루는 논문에는 "collagen peptide", "ACE inhibitory", "chitosan nanoaggregates", "hepatopancreas" 같은 고도의 의생명 전문 용어가 밀집되어 있다. PubMedBERT는 PubMed 30M+ 초록과 3M+ 전문으로 사전학습되어, 이러한 용어의 의미적 관계를 정확히 인코딩한다. 일반 BERT에서는 "chitosan"이 OOV 또는 희귀 토큰이지만, PubMedBERT에서는 빈출 토큰이다.

### 2.2 Vector Database: 왜 ChromaDB인가

| 후보 | 장점 | 단점 | 탈락 이유 |
|------|------|------|----------|
| **ChromaDB** (선택) | 로컬 파일 저장(PersistentClient), Python 네이티브, 메타데이터 저장/필터링 지원, 설치 간단 | 대규모(100만+) 시 FAISS보다 느림 | -- |
| FAISS | 검색 속도 최상, Meta 개발, 인덱스 최적화 옵션 다양 | 메타데이터 저장 불가(별도 관리 필요), API 저수준 | 메타데이터 관리 복잡 |
| Pinecone | 관리형 서비스, 확장성 우수 | 유료, 클라우드 의존, 데이터 외부 전송 | 비용, 로컬 실행 불가 |
| Weaviate | GraphQL API, 하이브리드 검색 | 서버 프로세스 필요, 설정 복잡 | 프로토타입에 과도한 인프라 |

핵심 논거: 5,590편 규모에서는 ChromaDB의 검색 성능이 충분하다(~수 ms). 메타데이터(PMID, title, year, journal, MeSH terms)를 벡터와 함께 단일 컬렉션에 저장할 수 있어, 검색 결과에서 즉시 논문 정보를 조회할 수 있다. 별도 서버 프로세스 없이 `PersistentClient`로 파일 시스템에 직접 저장/로드하므로 배포가 단순하다.

### 2.3 Embedding 전략: 왜 Abstract 단위 임베딩(No Chunking)인가

일반적인 RAG 시스템은 긴 문서를 chunk(예: 512 토큰 단위)로 나누어 임베딩한다. 이 시스템은 논문 초록 전체를 단일 벡터로 임베딩한다.

**근거**:

1. **초록의 길이 특성**: PubMed 논문 초록은 보통 150~350단어(200~500 토큰) 범위이다. PubMedBERT의 max_length=512 토큰 이내에 대부분 수용된다. 즉, chunking의 필요성 자체가 낮다.

2. **의미적 완결성**: 초록은 배경-목적-방법-결과-결론의 구조를 가진 자기 완결적 텍스트이다. 이를 쪼개면 "이 연구에서는 chitosan을 추출했다"와 "항균 활성을 보였다"가 분리되어, 두 정보의 연관성이 벡터에 반영되지 않는다.

3. **검색 단위 = 인용 단위**: 검색 결과가 곧 LLM에게 전달되는 인용 단위이다. chunk 단위 검색이면 같은 논문의 여러 chunk가 Top-K를 차지하여 다양성이 떨어질 수 있다. 논문 단위 검색은 5편의 서로 다른 논문을 보장한다.

**트레이드오프**: 512 토큰을 초과하는 긴 초록은 뒷부분이 truncation된다. 하지만 초록의 핵심 정보(목적, 주요 결과)는 보통 앞부분에 집중되어 있어, 정보 손실은 제한적이다.

### 2.4 Pooling 전략: 왜 Mean Pooling인가 ([CLS] 대신)

```python
# embed.py:46-52, retriever.py:22-28
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state    # (batch, seq_len, 768)
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    summed = torch.sum(token_embeddings * mask_expanded, dim=1)  # (batch, 768)
    counted = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)    # (batch, 768)
    return summed / counted                                       # (batch, 768)
```

BERT 계열 모델에서 문장 표현을 얻는 방법은 크게 두 가지이다:

| 방법 | 원리 | 장점 | 단점 |
|------|------|------|------|
| `[CLS]` 토큰 | 첫 번째 토큰의 출력 벡터 사용 | 간단 | NSP(Next Sentence Prediction) 태스크에 최적화되어 있어 문장 유사도에 부적합한 경우 있음 |
| **Mean Pooling** (선택) | 모든 토큰 벡터의 가중 평균 | 문장 전체 의미를 고르게 반영, Sentence-BERT 논문에서 우수성 입증 | [PAD] 토큰 제외를 위한 attention_mask 처리 필요 |

Mean pooling에서 `attention_mask`를 적용하는 이유: 배치 내 길이가 다른 텍스트는 `[PAD]` 토큰으로 채워진다. `[PAD]`의 출력 벡터는 무의미한 값이므로, mask를 곱하여 평균에서 제외한다. `torch.clamp(min=1e-9)`는 빈 시퀀스에서의 0-division 방지이다.

### 2.5 LLM: 왜 Claude Haiku인가

| 후보 | 입력 비용/MTok | 출력 비용/MTok | 품질 | 선택 이유 |
|------|-------------|--------------|------|----------|
| **Claude Haiku 4.5** (선택) | $0.80 | $4.00 | 요약/인용 태스크에 충분 | 비용 효율 최상, 프로토타입에 적합 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 더 정교한 추론 | 프로토타입에 과도한 비용 |
| Gemini 2.0 Flash (폴백) | 무료 (15 RPM) | 무료 | Haiku와 유사 | Rate limit, API 안정성 미확인 |

이 시스템에서 LLM의 역할은 "주어진 5편의 초록을 읽고 질문에 답변하면서 PMID를 인용"하는 것이다. 고도의 추론이나 창의적 생성이 아닌, 주어진 컨텍스트 내 정보 추출과 구조화된 요약이 핵심이다. Haiku급 모델로 충분하며, 질문당 비용이 약 $0.003(약 4원)으로 테스트 예산 내에서 1,500회 이상 질문이 가능하다.

Gemini Flash는 무료 티어를 활용할 수 있는 폴백으로 `config.py`에서 `LLM_BACKEND = "gemini"`로 전환 가능하다.

---

## 3. 데이터 흐름과 텐서 변환

### 3.1 데이터 원천: screened.csv

week_6에서 `keyword_screen.py`로 생성된 데이터이다.

```
원본: results_final.csv (PubMed에서 수집한 6,584편)
  |
  v  keyword_screen.py
  |  3개 키워드 그룹(PART x CATEGORY x FN) 모두 1개 이상 매칭 필터
  v
screened.csv (5,590편, 84.9% 통과율)
```

CSV 컬럼 구조 (11개):

| 컬럼 | 타입 | 용도 |
|------|------|------|
| `pmid` | int | PubMed 고유 ID, ChromaDB의 document ID로 사용 |
| `title` | str | 논문 제목, 메타데이터로 저장 |
| `abstract` | str | **임베딩 대상**, LLM 컨텍스트의 핵심 |
| `authors` | str | 저자 목록 (현재 미사용) |
| `journal` | str | 저널명, 메타데이터로 저장 |
| `year` | int | 출판 연도, 메타데이터로 저장 |
| `mesh_terms` | str | MeSH 용어, 메타데이터로 저장 |
| `abstract_clean` | str | 전처리된 초록 (현재 미사용, 원본 abstract 사용) |
| `kw_part` | str | 매칭된 부위 키워드 (현재 미사용) |
| `kw_category` | str | 매칭된 분류 키워드 (현재 미사용) |
| `kw_fn` | str | 매칭된 기능성 키워드 (현재 미사용) |

참고: CSV는 `utf-8-sig` 인코딩(BOM 포함)이며, `pd.read_csv(encoding="utf-8-sig")`로 읽는다.

### 3.2 Step 1: 임베딩 생성 (embed.py)

```
입력: screened.csv의 abstract 컬럼 (5,590개 텍스트)
  │
  │  NaN/빈 문자열 제거 후 유효 초록만 추출
  v
texts: List[str]  (len = 5,590)
  │
  ├─── Batch i (i=0..174, batch_size=32) ─────────────────────────┐
  │                                                                │
  │  tokenizer(batch, padding=True, truncation=True,               │
  │            max_length=512, return_tensors="pt")                 │
  │  → input_ids:      (32, seq_len)   dtype=int64                 │
  │  → attention_mask:  (32, seq_len)   dtype=int64                │
  │  │  seq_len: 배치 내 최대 길이까지 패딩 (최대 512)               │
  │  v                                                              │
  │  model(**encoded)                                               │
  │  → last_hidden_state: (32, seq_len, 768)  dtype=float32        │
  │  │                                                              │
  │  v  mean_pooling(output, attention_mask)                        │
  │  → token_embeddings:  (32, seq_len, 768)                       │
  │  → mask_expanded:     (32, seq_len, 768)  # 0/1 마스크          │
  │  → summed:            (32, 768)           # 마스크 적용 합산     │
  │  → counted:           (32, 768)           # 유효 토큰 수         │
  │  → result:            (32, 768)           # 요소별 나눗셈        │
  │  │                                                              │
  │  v  .cpu().numpy()                                              │
  │  → numpy array:       (32, 768)  dtype=float32                 │
  │                                                                │
  └─── 50 배치마다 checkpoint 저장 ────────────────────────────────┘
  │
  v  np.vstack(all_chunks)
embeddings.npy: (5590, 768)  dtype=float32  약 34MB
pmids.csv:      5,590행 (pmid 컬럼 1개)
```

**메모리 사용량 추정**:
- 모델 파라미터: ~110M params x 4 bytes = ~440MB
- 배치 중간 텐서: (32, 512, 768) x 4 bytes = ~50MB
- 최종 출력: (5590, 768) x 4 bytes = ~17MB (float32), 디스크에는 ~34MB(.npy 오버헤드 포함)

### 3.3 Step 2: ChromaDB 구축 (build_db.py)

```
입력:
  embeddings.npy  (5590, 768)    ← Step 1 출력
  pmids.csv       (5590행)        ← Step 1 출력
  screened.csv    (5590행, 11컬럼) ← 원본 데이터(메타데이터 소스)
  │
  v  PMID set 기반 필터링 (pmids.csv의 PMID 집합과 screened.csv 교집합)
  │  → 정합성 보장: embeddings[i] ↔ df.iloc[i] ↔ pmids_df.iloc[i]
  │
  v  배치 500건씩 collection.add()
  │
  │  ChromaDB에 저장되는 데이터 (문서당):
  │  ┌──────────────────────────────────────────────────────┐
  │  │  id:        str(pmid)         예: "30047062"         │
  │  │  embedding: List[float]       768개 float             │
  │  │  document:  str               초록 원문 전체           │
  │  │  metadata:  dict                                      │
  │  │    ├─ pmid:       str                                 │
  │  │    ├─ title:      str         (최대 500자 truncate)   │
  │  │    ├─ year:       int         (NaN → 0)               │
  │  │    ├─ journal:    str         (최대 200자 truncate)   │
  │  │    └─ mesh_terms: str         (최대 500자 truncate)   │
  │  └──────────────────────────────────────────────────────┘
  v
chroma_db/  (~100MB, SQLite 기반)
  ├── chroma.sqlite3     # 메타데이터 + 인덱스
  └── *.bin              # 벡터 데이터
```

### 3.4 Step 3: 질의 응답 (chatbot.py → retriever.py → llm.py)

```
User Query (영어 텍스트)
  │
  v  Retriever._embed_query()
  │  tokenizer([query], padding=True, truncation=True,
  │            max_length=512, return_tensors="pt")
  │  → input_ids:      (1, seq_len)
  │  → attention_mask:  (1, seq_len)
  │  │
  │  v  model forward + mean_pooling
  │  → query_vector:   (768,)  List[float]
  │
  v  ChromaDB collection.query()
  │  query_embeddings=[query_vector], n_results=5
  │  → L2 distance 기준 Top-5 논문 반환
  │  → 각 결과: {id, document, metadata, distance}
  │
  v  llm._build_prompt(question, papers)
  │  ┌──────────────────────────────────────────────┐
  │  │  CONTEXT_TEMPLATE x 5편:                     │
  │  │    [Paper 1] PMID: 30047062 | 2018 | J Fish  │
  │  │    Title: Methods for Assessments of...       │
  │  │    Abstract: (최대 1,500자 truncate)          │
  │  │    ...                                        │
  │  │  [Paper 5] PMID: 37931446 | 2024 | ...       │
  │  │                                               │
  │  │  ---                                          │
  │  │  Question: {user_query}                       │
  │  └──────────────────────────────────────────────┘
  │
  v  Claude/Gemini API 호출
  │  system=SYSTEM_PROMPT
  │  messages=[{"role": "user", "content": user_message}]
  │  max_tokens=1024
  │
  v
Answer (PMID 인용 포함 구조화된 텍스트)
```

---

## 4. 벡터 공간과 검색 분석

### 4.1 768차원 공간의 의미

PubMedBERT의 출력 768차원 벡터는 초록 텍스트의 의미적 요약이다. 이 공간에서:

- "chitosan antimicrobial activity from crustacean shells"와 관련된 논문들은 서로 가까이 위치
- "astaxanthin photoprotection"과 관련된 논문들은 다른 영역에 클러스터링
- 두 주제 모두 다루는 논문은 두 클러스터 사이에 위치

5,590개의 768차원 벡터가 이 공간에 분포하고 있으며, 쿼리 벡터와의 거리가 가장 가까운 K개를 검색한다.

### 4.2 Distance Metric

ChromaDB는 기본적으로 **Squared L2 Distance** (유클리드 거리의 제곱)를 사용한다.

```
d(q, d) = sum_{i=1}^{768} (q_i - d_i)^2
```

`collection.create()` 시 별도의 distance function을 지정하지 않았으므로 (`build_db.py:55-58`), ChromaDB의 default인 `"l2"`가 적용된다.

참고: ChromaDB에서 지원하는 다른 거리 함수로 `"cosine"`, `"ip"` (inner product)가 있지만, L2를 선택한 것은 ChromaDB default를 그대로 사용한 것이다. PubMedBERT 출력이 L2-normalized되지 않으므로, cosine distance가 이론적으로 더 적절할 수 있으나, 현재 규모에서 실질적 차이는 크지 않다.

### 4.3 실측 거리 범위 분석

테스트 로그에서 관찰된 실제 distance 값:

**Test 1: "antioxidant activity of fish collagen peptide"**
(`Docs/logs/test1.md`)

| 순위 | PMID | Distance | 제목 (일부) |
|------|------|----------|------------|
| 1 | 30047062 | 16.6652 | Methods for Assessments of Collagenolytic Activity... |
| 2 | 29874447 | 16.7669 | Biologically Active Substances from Marine Hydrobionts... |
| 3 | 19351034 | 16.8590 | The textile materials containing chitosan... |
| 4 | 21699985 | 16.8851 | Anti-baculovirus activity in a protein extracted... |
| 5 | 37931446 | 17.0665 | Differentiation of protein types extracted from tilapia... |

**Test 2: "chitosan antimicrobial activity from crustacean shells"**
(`Docs/logs/test2.md`)

검색 결과 5편 반환, distance 미출력 (tee 로그에서 truncate)

**검증 쿼리: 자기 자신 검색** (`build_db.py` 내장 테스트)

| 순위 | Distance | 의미 |
|------|----------|------|
| 1 | 0.0000 | 자기 자신 (완전 일치) |
| 2 | ~4.2 | 같은 하위 주제 |
| 3~5 | ~5.1~6.0 | 관련 주제 |

**관찰된 패턴**:

- 자기 자신과의 거리: 정확히 0
- 같은 좁은 주제(narrow topic): 약 4~8 범위
- 쿼리-문서 간 거리: 약 16~18 범위 (쿼리와 문서의 텍스트 길이/구조 차이가 반영됨)
- Top-1과 Top-5의 거리 차이가 작음 (~0.4 범위): 쿼리와 비슷한 관련도의 논문이 여러 편 존재

쿼리-문서 간 거리(~16~17)가 문서-문서 간 거리(~4~6)보다 훨씬 큰 이유: 쿼리는 짧은 구(phrase) 형태이고 문서는 300단어 이상의 초록이다. Mean pooling 결과 벡터의 norm이 다르기 때문에, 같은 주제라도 절대 거리가 크게 나타난다. 이는 L2 distance의 특성이며, cosine distance를 사용하면 이 차이가 줄어들 수 있다.

### 4.4 검색 품질에 영향을 미치는 요인

**잘 동작하는 쿼리 유형**:
- 구체적인 물질명 + 활성 유형: "chitosan antimicrobial activity from crustacean shells"
- PubMed 초록에서 흔히 사용되는 학술 표현: "ACE inhibitory peptides from marine sources"

**검색 품질이 떨어질 수 있는 경우**:
- 한국어 쿼리: PubMedBERT는 영어 전용 모델이므로 한국어 토큰은 모두 `[UNK]`로 처리됨
- 지나치게 짧은 쿼리 ("collagen"): 의미적 구분력이 낮아 관련 없는 논문도 상위에 올라올 수 있음
- 데이터셋에 해당 주제 논문이 적은 경우: Test 1에서 "fish collagen peptide antioxidant" 쿼리에 정확히 부합하는 논문이 부족하여, 간접적으로 관련된 논문이 검색됨

### 4.5 단일 벡터 검색의 한계

문서당 단일 벡터는 초록의 모든 측면을 768차원에 압축한다. "chitosan extraction AND antimicrobial activity AND wound healing"처럼 복수의 측면을 동시에 요구하는 쿼리는, 각 측면의 의미가 평균화되어 표현력이 떨어진다. 이 한계는 multi-vector 표현(ColBERT 등)이나 reranking 단계를 추가하면 개선할 수 있다.

---

## 5. Prompt Engineering

### 5.1 System Prompt 설계 (`config.py:67-75`)

```
You are a research assistant specializing in fishery byproduct bioactivity.

Rules:
- Answer based ONLY on the provided PubMed abstracts.
- Cite every claim with the paper's PMID, e.g. (PMID: 12345678).
- If the provided papers do not contain relevant information, say so explicitly.
- Structure your answer: (1) Key findings, (2) Supporting details per paper, (3) Cited paper list.
```

설계 원칙:

1. **역할 제한** ("research assistant specializing in..."): LLM의 응답 범위를 수산부산물 연구로 좁힌다.

2. **Grounding 강제** ("based ONLY on the provided PubMed abstracts"): 가장 중요한 규칙. LLM이 사전학습된 일반 지식으로 답변하는 것(hallucination)을 방지한다. Test 1의 결과에서 실제로 "there is no direct information about the antioxidant activity of fish collagen peptides"라고 명시적으로 한계를 밝힌 것은 이 규칙이 작동한 증거이다.

3. **인용 형식 지정** ("Cite every claim with the paper's PMID"): PMID 인용을 강제하여 답변의 추적 가능성(traceability)을 보장한다. 사용자는 `https://pubmed.ncbi.nlm.nih.gov/{PMID}`로 원문을 즉시 확인할 수 있다.

4. **구조화된 출력** ("(1) Key findings, (2) Supporting details, (3) Cited paper list"): 답변의 일관된 형식을 유도한다. 매번 다른 구조로 답하면 사용자 경험이 나빠진다.

5. **명시적 불확실성 표현** ("say so explicitly"): 관련 논문이 없을 때 "잘 모르겠습니다"가 아니라 "제공된 논문에서 관련 정보를 찾지 못했습니다"라고 구체적으로 밝히도록 유도한다.

### 5.2 Context Window 예산 계산

Claude Haiku 4.5의 context window: 200K 토큰. 이 시스템에서의 실사용량:

```
시스템 프롬프트:              ~100 토큰
─────────────────────────────
논문 5편 컨텍스트:
  [Paper i] 메타데이터 행     ~30 토큰 x 5 = ~150 토큰
  Title 행                    ~20 토큰 x 5 = ~100 토큰
  Abstract (1,500자 제한)     ~500 토큰 x 5 = ~2,500 토큰
  소계                        ~2,750 토큰
─────────────────────────────
질문:                         ~20 토큰
프롬프트 템플릿 오버헤드:       ~30 토큰
─────────────────────────────
입력 합계:                    ~2,900~3,100 토큰

출력 (max_tokens=1024):       ~300~700 토큰 (실측)
─────────────────────────────
총 사용량:                    ~3,200~3,800 토큰
```

200K context window의 약 1.5~2%만 사용한다. 상당한 여유가 있으며, 필요시 Top-K를 20으로 늘려도 약 12,000 토큰 수준으로 충분히 수용 가능하다.

### 5.3 왜 Abstract를 1,500자로 Truncate하는가

`llm.py:29`에서 `p["abstract"][:1500]`으로 초록을 자른다.

- 영어 기준 1,500자 ≈ 350~400단어 ≈ 500~600 토큰
- 대부분의 초록 전문이 이 범위 안에 들어간다
- 극히 일부의 매우 긴 초록(방법론 상세 기술 등)만 truncation 영향을 받음
- 목적: LLM 입력 토큰 수를 예측 가능한 범위로 제한하여 비용을 안정화

이 truncation은 토큰 단위가 아니라 문자 단위이다. 이론적으로는 토큰 단위 truncation이 더 정확하지만, 실용적으로 1,500자 제한은 충분히 보수적인 상한이다.

### 5.4 Context Template 구조

```python
# config.py:86-90
CONTEXT_TEMPLATE = """\
[Paper {i}] PMID: {pmid} | {year} | {journal}
Title: {title}
Abstract: {abstract}
"""
```

각 논문을 `[Paper {i}]`로 번호를 매겨 LLM이 참조하기 쉽게 한다. PMID, 연도, 저널을 첫 줄에 배치하여 LLM이 인용 시 이 정보를 쉽게 찾을 수 있도록 한다.

---

## 6. 오류 처리와 복원력

### 6.1 Checkpoint 시스템 (embed.py)

5,590편을 batch_size=32로 처리하면 총 약 175 배치, Intel Mac MPS에서 60~90분이 소요된다. 중간에 프로세스가 종료되면 전체를 다시 실행해야 하는 문제를 방지한다.

```
embed.py 실행 흐름:

Batch 0..49   → checkpoint chunk_0000.npy 저장 (1,600건)
Batch 50..99  → checkpoint chunk_0001.npy 저장 (1,600건)
Batch 100..149 → checkpoint chunk_0002.npy 저장 (1,600건)
Batch 150..174 → checkpoint chunk_0003.npy 저장 (잔여)

─── 만약 Batch 120에서 크래시 발생 ───

재시작 시:
  load_checkpoint() → chunk_0000.npy + chunk_0001.npy 로드 (3,200건)
  start_batch = 3200 / 32 = 100
  Batch 100부터 재개
```

**50배치 간격의 근거**: 50 x 32 = 1,600건 ≈ 전체의 29%. 체크포인트 3~4개면 전체를 커버한다. 너무 잦으면 디스크 I/O 오버헤드가 발생하고, 너무 뜸하면 크래시 시 손실이 크다. 50배치는 약 15~25분 간격으로, 실용적 균형점이다.

완료 후 체크포인트 파일은 자동 삭제된다 (`embed.py:199-203`).

### 6.2 MPS 메모리 관리

```bash
# run_all.sh:12
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

PyTorch의 MPS(Metal Performance Shaders) 백엔드는 기본적으로 메모리 high watermark를 설정하여, 이전 피크 사용량 이상으로 할당을 허용하지 않는다. 대량 배치 처리에서 메모리 사용 패턴이 불규칙하면 이 제한에 걸려 OOM이 발생할 수 있다.

`RATIO=0.0`은 이 watermark를 해제하여, OS가 허용하는 한 메모리를 자유롭게 할당한다. 이 설정이 없으면 shard 분할이 필요했으나, 설정 후에는 전체 5,590편을 한 번에 처리할 수 있게 되었다.

### 6.3 Shard 방식과 PMID 순서 문제

초기에는 MPS 메모리 제한으로 인해 screened.csv를 3개 shard로 분할하여 처리하는 방식을 사용했다:

```bash
python 01_embedding/embed.py data/screened_1of3.csv
python 01_embedding/embed.py data/screened_2of3.csv
python 01_embedding/embed.py data/screened_3of3.csv
```

이때 round-robin 방식으로 행을 나누면 PMID 순서가 뒤섞이는 문제가 발생한다:

```
원본:    [P1, P2, P3, P4, P5, P6]
1of3:   [P1, P4]
2of3:   [P2, P5]
3of3:   [P3, P6]
병합:   [P1, P4, P2, P5, P3, P6]  ← 원본과 순서 불일치
```

`build_db.py`는 `pmids.csv`와 `screened.csv`를 PMID set 기반으로 조인하여 이 순서 문제를 해결한다 (`build_db.py:36-39`). 궁극적으로는 `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` 설정으로 shard 없이 전체 처리가 가능해져 이 문제를 근본적으로 회피했다.

### 6.4 API 에러 처리 (llm.py)

```python
# llm.py:53-58 (Claude backend)
except anthropic.AuthenticationError:
    return "[Error] Invalid API key. Check ANTHROPIC_API_KEY."
except anthropic.BadRequestError as e:
    return f"[Error] {e}"
except anthropic.APIError as e:
    return f"[Error] {e}"

# llm.py:77-78 (Gemini backend)
except Exception as e:
    return f"[Error] Gemini: {e}"
```

에러가 발생해도 프로그램이 종료되지 않고, `[Error]` 접두사가 붙은 메시지를 반환한다. 사용자는 다음 질문을 계속 입력할 수 있다. 실제로 초기 테스트에서 `ANTHROPIC_API_KEY`가 터미널 세션에 로드되지 않아 `AuthenticationError`가 발생했으며, `run_all.sh`에 `source ~/.anthropic_key` 로직을 추가하여 해결했다.

### 6.5 LLM 백엔드 폴백

```python
# llm.py:81-87
def create_llm(backend=None):
    backend = backend or LLM_BACKEND    # config.py에서 "claude" 또는 "gemini"
    if backend == "gemini":
        return GeminiLLM()
    else:
        return ClaudeLLM()
```

Claude API에 문제가 있거나 크레딧이 소진되면, `config.py`에서 `LLM_BACKEND = "gemini"`로 변경하여 무료 Gemini Flash로 전환할 수 있다. 코드 수정 없이 설정만 변경하면 된다. 다만, 런타임 자동 폴백(Claude 실패 시 자동으로 Gemini 시도)은 아직 구현되어 있지 않다.

### 6.6 기타 방어적 처리

| 위치 | 처리 | 목적 |
|------|------|------|
| `embed.py:167-168` | `dropna(subset=[COL_ABSTRACT])` + 빈 문자열 제거 | abstract가 없는 행으로 인한 에러 방지 |
| `build_db.py:31-32` | `assert len(pmids_df) == embeddings.shape[0]` | 임베딩과 PMID 매핑 불일치 조기 감지 |
| `build_db.py:75` | `int(row[COL_YEAR]) if pd.notna(...)` else 0 | NaN year로 인한 ChromaDB 메타데이터 에러 방지 |
| `build_db.py:73,76,77` | 메타데이터 문자열 truncation (500/200/500자) | ChromaDB 메타데이터 크기 제한 준수 |
| `retriever.py:35-37` | `Path(chroma_path).exists()` 검사 | DB 미빌드 상태에서의 명확한 에러 메시지 |
| `chatbot.py:69` | `1 <= new_k <= 20` 범위 검사 | 비합리적인 Top-K 설정 방지 |
| `run_all.sh:12-13` | `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`, `TOKENIZERS_PARALLELISM=false` | MPS OOM 방지, tokenizer fork 경고 억제 |
| `run_all.sh:22-25` | embeddings.npy 존재 시 Step 1 스킵 | 불필요한 재임베딩 방지 (60~90분 절약) |

---

## 7. 성능 특성

테스트 환경: Intel Mac, MPS (Metal Performance Shaders), Python 3.12.12

### 7.1 단계별 소요 시간

| 단계 | 소요 시간 | 주요 병목 |
|------|----------|----------|
| 임베딩 생성 (5,590편) | 60~90분 | Transformer forward pass (175 배치 x 약 20~30초/배치) |
| ChromaDB 빌드 (5,590건) | 1~2분 | 디스크 I/O (12 배치 x 500건) |
| PubMedBERT 모델 로드 | ~10초 | 디스크 → 메모리 → MPS 디바이스 전송 |
| **쿼리 임베딩** | **~1.0초** | 단일 텍스트 tokenize + forward pass |
| **ChromaDB 검색** | **~0.2초** | L2 nearest neighbor (5,590건 규모) |
| **검색 합계** | **~1.2초** | 임베딩 + 검색 |
| **LLM 답변 생성** | **4~7초** | API 네트워크 지연 + 토큰 생성 |
| **총 질문-답변** | **~5~8초** | 검색 + 생성 합산 |

### 7.2 Throughput

- 임베딩 생성: 약 62~93편/분 (5,590편 / 60~90분)
- 질의응답: 약 7~12 질문/분 (네트워크 상태에 따라 변동)

### 7.3 스토리지

| 아티팩트 | 크기 | 비고 |
|---------|------|------|
| screened.csv | ~20MB | 원본 데이터 |
| embeddings.npy | ~34MB | (5590, 768) float32 |
| pmids.csv | ~60KB | 5,590행 |
| chroma_db/ | ~100MB | SQLite + 벡터 바이너리 |
| PubMedBERT 모델 캐시 | ~500MB | `~/.cache/huggingface/` (첫 실행 시 다운로드) |
| **총 디스크 사용** | **~650MB** | 모델 캐시 포함 |

### 7.4 비용

Claude Haiku 4.5 기준:

| 항목 | 토큰 수 | 비용 |
|------|---------|------|
| 입력 (시스템 + 논문 5편 + 질문) | ~3,000~5,000 | ~$0.0024~$0.004 |
| 출력 (답변) | ~300~700 | ~$0.0012~$0.0028 |
| **질문 1건당 합계** | | **~$0.003~0.007** |
| $5 충전 시 | | ~700~1,500건 질문 |

---

## 8. 한계와 알려진 문제

### 8.1 영어 전용 쿼리

PubMedBERT는 영어 텍스트로만 학습되었다. 한국어 쿼리를 입력하면 모든 토큰이 `[UNK]`로 처리되어, 의미 없는 벡터가 생성된다. 결과적으로 검색 결과가 무작위에 가까워진다.

현재 워크어라운드: 사용자가 직접 영어로 질문한다.

### 8.2 Reranking 부재

검색 결과는 PubMedBERT의 bi-encoder 기반 L2 거리만으로 정렬된다. Cross-encoder 기반 reranker가 없으므로, 쿼리와 문서 간의 세밀한 의미적 관련성을 평가하지 못한다. Test 1에서 "antioxidant activity of fish collagen peptide" 쿼리에 collagenolytic activity(콜라겐 분해 활성) 논문이 1위로 검색된 것은, bi-encoder가 "collagen"이라는 단어의 출현에 과도하게 반응한 결과일 수 있다.

### 8.3 Single-turn 대화

현재 시스템은 대화 히스토리를 유지하지 않는다. 매 질문이 독립적으로 처리된다.

```
Query> What is chitosan?
  → 답변 생성

Query> What about its antimicrobial activity?
  → "its"가 무엇을 가리키는지 알 수 없음
  → chitosan과 무관한 결과가 나올 수 있음
```

`chatbot.py`의 `last_papers` 변수는 단순히 `papers` 명령어를 위한 것이며, LLM 컨텍스트에는 포함되지 않는다.

### 8.4 초록만 사용 (전문 미포함)

PubMed 논문의 초록만 임베딩/검색에 사용된다. 전문(full text)에 포함된 상세 실험 조건, 수치 데이터, 고찰 내용은 반영되지 않는다. 특히 "어떤 농도에서 최대 활성을 보이는가" 같은 정량적 질문에는 초록만으로 답변이 불충분할 수 있다.

### 8.5 Distance Score 해석의 어려움

ChromaDB가 반환하는 L2 distance는 정규화되지 않은 절대값이다. "이 거리 이하면 관련 있음"이라는 명확한 임계값을 설정하기 어렵다. Test 1에서 Top-1(dist=16.6652)과 Top-5(dist=17.0665)의 차이가 0.4에 불과하여, "관련 논문이 5편 있다"와 "관련 논문이 1편뿐이고 나머지는 노이즈"를 구분하기 어렵다.

### 8.6 정적 인덱스

논문 데이터가 추가되면 전체 파이프라인(임베딩 → ChromaDB)을 다시 실행해야 한다. 점진적(incremental) 임베딩 추가는 지원되나(ChromaDB의 `collection.add()`), 기존 체크포인트 시스템과의 연동은 구현되어 있지 않다.

### 8.7 검색 결과 다양성 미보장

Top-K 결과가 모두 매우 유사한 주제의 논문일 수 있다. 예를 들어, "chitosan applications" 쿼리에 5편 모두 chitosan antimicrobial 논문이 나오면, wound healing, food preservation 등 다른 응용 분야의 정보가 누락된다. MMR(Maximal Marginal Relevance) 같은 다양성 알고리즘이 적용되어 있지 않다.

---

## 9. 향후 개선 방향

| 개선 사항 | 효과 | 복잡도 |
|----------|------|--------|
| **한국어 쿼리 번역**: 한국어 입력 → LLM으로 영어 변환 → 검색 → 한국어 답변 | 사용자 접근성 대폭 향상 | 낮음 (LLM 호출 1회 추가) |
| **Hybrid Search**: 벡터 검색 + BM25 키워드 검색 결합 | 특정 물질명/PMID 등 정확 매칭 쿼리 성능 향상 | 중간 |
| **Cross-encoder Reranking**: Top-20 검색 후 cross-encoder로 Top-5 재정렬 | 검색 정확도 향상 (특히 미묘한 관련성 구분) | 중간 |
| **Multi-turn 대화**: 이전 질문/답변을 LLM 컨텍스트에 포함 | 후속 질문, 심화 질문 지원 | 낮음 (메시지 리스트 유지) |
| **Streamlit UI**: 웹 브라우저 기반 인터페이스 | 비개발자 사용 가능, 결과 시각화 | 낮음~중간 |
| **Metadata 필터링**: "2020년 이후 논문만" 같은 조건 추가 | 검색 정밀도 향상 | 낮음 (ChromaDB where 절) |
| **Distance → Cosine 전환**: ChromaDB collection 생성 시 `metadata={"hnsw:space": "cosine"}` | 쿼리-문서 간 거리 scale 개선 | 낮음 (DB 재빌드 필요) |
| **자동 폴백**: Claude 실패 시 자동 Gemini 전환 | 가용성 향상 | 낮음 |

---

## 부록: 파일별 역할 요약

| 파일 | 줄 수 | 핵심 역할 |
|------|------|----------|
| `config.py` | 91 | 모든 설정의 단일 진실 공급원. 경로 12개, 하이퍼파라미터 7개, 프롬프트 3개 정의 |
| `01_embedding/embed.py` | 209 | PubMedBERT 로드 → 배치 임베딩 → checkpoint 저장/복구 → .npy 출력 |
| `02_vectordb/build_db.py` | 133 | embeddings.npy + screened.csv → ChromaDB 적재 → 검증 쿼리 실행 |
| `03_chatbot/retriever.py` | 87 | PubMedBERT 쿼리 임베딩 + ChromaDB Top-K 검색. `Retriever` 클래스 |
| `03_chatbot/llm.py` | 92 | 프롬프트 조립 + Claude/Gemini API 호출. `ClaudeLLM`, `GeminiLLM` 클래스 |
| `03_chatbot/chatbot.py` | 111 | CLI REPL 루프. 명령어 파싱, 타이밍 출력, `last_papers` 관리 |
| `run_all.sh` | 55 | 환경 설정 → 임베딩(스킵 가능) → DB 빌드 → 챗봇 실행. 자동 로그 생성 |
