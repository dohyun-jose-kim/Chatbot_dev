# 03. 챗봇 모듈

챗봇은 세 개의 모듈로 구성된다: `retriever.py` (검색), `llm.py` (답변 생성), `chatbot.py` (CLI 인터페이스).

---

## 모듈 구조

```
03_chatbot/
    ├── retriever.py    # ChromaDB 검색 + PubMedBERT 쿼리 임베딩
    ├── llm.py          # Claude/Gemini API 호출, 프롬프트 조립
    └── chatbot.py      # CLI 메인 루프, 명령어 처리
```

---

## retriever.py -- 논문 검색

### 역할

사용자의 질문을 PubMedBERT로 임베딩하고, ChromaDB에서 가장 유사한 논문 Top-K편을 검색한다.

### 동작 과정

```
사용자 질문 (영어 텍스트)
    |
    v  _embed_query()
PubMedBERT Tokenizer로 토큰화 (max_length=512)
    |
    v  Transformer Forward Pass
768차원 벡터 생성 (mean pooling)
    |
    v  search()
ChromaDB.query()로 L2 거리 기준 Top-K 검색
    |
    v
[{pmid, abstract, title, year, journal, mesh_terms, distance}, ...]
```

### 핵심 설계

- **mean_pooling 일관성**: `embed.py`에서 논문 임베딩을 생성할 때 사용한 것과 동일한 mean pooling 로직을 복사하여 사용한다. 같은 벡터 공간에서 비교해야 검색 품질이 보장된다.
- **초기화 시 모델 로드**: `Retriever` 클래스 생성 시 PubMedBERT 모델과 ChromaDB 클라이언트를 한 번만 로드한다. 이후 검색은 쿼리 임베딩 + DB 쿼리만 수행하므로 빠르다(약 1.2초).
- **디바이스 자동 선택**: MPS 사용 가능 시 MPS, 아니면 CPU로 폴백.

---

## llm.py -- 답변 생성

### 역할

검색된 논문과 질문을 조합하여 LLM에게 전송하고, PMID 인용이 포함된 답변을 받는다.

### 지원 백엔드

| 백엔드 | 모델 | 비용 | 설정 |
|--------|------|------|------|
| **Claude** (기본) | `claude-haiku-4-5-20251001` | ~$0.003/질문 | `ANTHROPIC_API_KEY` 필요 |
| **Gemini** (폴백) | `gemini-2.0-flash` | 무료 (15 RPM) | `GEMINI_API_KEY` 필요 |

`config.py`에서 `LLM_BACKEND = "claude"` 또는 `"gemini"`로 변경할 수 있다.

### 프롬프트 구성

LLM에게 전달되는 프롬프트는 세 부분으로 구성된다:

**1. 시스템 프롬프트 (~100 토큰)**
```
You are a research assistant specializing in fishery byproduct bioactivity.
Rules:
- Answer based ONLY on the provided PubMed abstracts.
- Cite every claim with the paper's PMID, e.g. (PMID: 12345678).
- If the provided papers do not contain relevant information, say so explicitly.
- Structure your answer: (1) Key findings, (2) Supporting details per paper, (3) Cited paper list.
```

**2. 컨텍스트 -- 검색된 논문 초록 (~3,000~5,000 토큰)**
```
[Paper 1] PMID: 30047062 | 2018 | J Fish Biol
Title: Methods for Assessments of...
Abstract: Collagen was extracted from... (최대 1,500자)
```
각 논문의 초록을 1,500자까지 잘라서 토큰 비용을 절약한다.

**3. 사용자 질문 (~20 토큰)**

### 에러 처리

- `AuthenticationError`: API 키가 잘못되었거나 설정되지 않은 경우
- `BadRequestError`: 프롬프트가 모델 한도를 초과한 경우
- `APIError`: 네트워크 오류 등 기타 API 문제

모든 에러는 `[Error]` 접두사와 함께 메시지로 반환되며, 프로그램이 종료되지 않는다.

---

## chatbot.py -- CLI 인터페이스

### 실행 방법

```bash
cd /Users/inco/01_Projects/00_Tasks/ifc_ojt_dh.kim/week_7/RAG_Pipeline
bash run_all.sh
```

또는 직접 실행:
```bash
source ~/.anthropic_key
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python 03_chatbot/chatbot.py
```

### CLI 명령어

| 명령어 | 설명 |
|--------|------|
| `quit` / `q` | 챗봇 종료 |
| `k <숫자>` | 검색 논문 수 변경 (기본 5, 범위 1~20) |
| `papers` | 마지막 검색에서 반환된 논문 목록 표시 (PMID, 연도, 거리, 제목) |
| `help` | 명령어 도움말 표시 |
| 그 외 | 질문으로 처리 -> RAG 파이프라인 실행 |

### 질문-답변 흐름

```
Query> antioxidant activity of fish collagen peptide

  Searching (top-5)...
  Found 5 papers (1.2s)
    [1] PMID:30047062 | Methods for Assessments of Collagenolytic...
    [2] PMID:29874447 | Biologically Active Substances from Marine...
    ...

  Generating answer...

────────────────────────────────────────────────────────────
# Antioxidant Activity of Fish Collagen Peptides
## Key Findings
...답변 내용...
────────────────────────────────────────────────────────────
  (search 1.2s + generation 4.1s)
```

---

## 비용 계산

Claude Haiku 기준 질문 1건당 예상 토큰 사용량:

| 항목 | 토큰 수 | 비용 |
|------|---------|------|
| 시스템 프롬프트 (입력) | ~100 | |
| 논문 5편 초록 (입력) | ~3,000~5,000 | |
| 질문 (입력) | ~20 | |
| **입력 합계** | ~3,120~5,120 | ~$0.0025~$0.004 |
| 답변 (출력) | ~300~500 | ~$0.0012~$0.002 |
| **총 비용** | | **~$0.003/질문** |

$5 충전 시 약 1,500건 질문이 가능하다.
