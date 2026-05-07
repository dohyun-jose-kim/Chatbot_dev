# NLP 고도화 파이프라인 진행 현황

> 마지막 업데이트: 2026-03-27

## 파이프라인 전체 구조

```
results_final.csv (6,584편)
        │
        ▼
  Phase 1: 키워드 스크리닝        ✅ 완료
        │
        ▼
  screened.csv (5,590편, 84.9%)
        │
        ▼
  Phase 1.5: LLM 스크리닝        ⚠️ 대안 탐색 중
        │
        ▼
  screened_llm.csv (?편)
        │
        ▼
  Phase 3: PubMedBERT 임베딩      📝 코드 작성 완료, 실행 대기
        │
        ▼
  Phase 4: Chroma VectorDB        📝 코드 작성 완료, 실행 대기
```

---

## Phase 1: 키워드 스크리닝 — ✅ 완료

- 스크립트: `01_screening/keyword_screen.py`
- PubMed 검색 쿼리의 PART/CATEGORY/FN 3개 그룹 키워드로 필터링
- 3그룹 모두 1개 이상 매칭된 논문만 통과
- 결과: 6,584편 → **5,590편 (84.9%)**
- 출력: `outputs/screened.csv`

## Phase 1.5: LLM 스크리닝 — ⚠️ 대안 탐색 중

- 스크립트: `01_screening/llm_screen.py`
- 목적: 키워드는 매칭되지만 실제 주제와 동떨어진 논문을 LLM으로 걸러내기

### 시도 1: Ollama gemma3:4b (로컬)
- Intel Mac에서 건당 1~2분 소요
- 5,590편 기준 약 140시간 → **비현실적, 중단**

### 시도 2: Ollama gemma3:1b (로컬)
- 건당 약 35초로 개선되었으나 5,590편 기준 약 54시간
- 30편 샘플 테스트 결과: 7편 수동 검증 중 **3편만 일치 (43% 정확도)**
- **판정 품질 부족, 중단**

### 현재 상태
로컬 LLM(Ollama)은 Intel Mac에서 속도와 품질 모두 부족하다는 결론.

### 확인된 대안

| 대안 | 장점 | 단점 |
|------|------|------|
| **Claude API 무료 티어** | 품질 높음, 비용 0원 | 분당 5건 제한 (5,590편 → ~19시간) |
| Claude API 유료 | 품질 높음, 빠름 | 비용 발생 (~$4) |
| M2 Mac에서 Ollama | 무료, Metal GPU로 속도 향상 | 별도 세팅 필요, 품질은 모델 의존 |
| 프롬프트 개선 후 재시도 | 추가 비용 없음 | 1b 모델 자체의 한계 가능성 |

---

## Phase 3: PubMedBERT 임베딩 — 📝 실행 대기

- 스크립트: `02_embedding/embed_pubmedbert.py`
- 모델: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`
- abstract → 768차원 벡터 (mean pooling)
- 필요 패키지: `transformers`, `torch` (설치 완료)
- **Phase 1.5 해결 후 실행**

## Phase 4: Chroma VectorDB — 📝 실행 대기

- 스크립트: `03_vectordb/build_chromadb.py`
- 임베딩 + 메타데이터(PMID, year, MeSH, title, journal)를 Chroma에 저장
- 필요 패키지: `chromadb` (설치 완료)
- **Phase 3 이후 실행**

---

## 다음에 해야 할 일

1. **LLM 스크리닝 대안 결정**
   - Claude API 무료 티어로 30편 재테스트 → 품질 확인
   - API 키 발급 필요: [console.anthropic.com](https://console.anthropic.com) → API Keys

2. **LLM 스크리닝 품질 확인 후**
   - 품질 OK → 전체 5,590편 실행
   - 품질 부족 → 프롬프트 개선 또는 다른 접근법 논의

3. **Phase 3, 4 실행**
   - LLM 스크리닝 완료 후 순차 실행
   - 또는 LLM 스크리닝 없이 5,590편 전체를 VectorDB에 넣는 방법도 가능

---

## 관련 문서

- `docs/01_llm_screening_ollama.md` — Ollama 도입 배경, 모델 비교, 변경 이력
- `plan1-20260327.md` — 전체 설계 (청킹, 임베딩 모델, VectorDB 결정)
- `Plan2-00.md` — 초기 구상 (스크리닝 2단계 아이디어)
