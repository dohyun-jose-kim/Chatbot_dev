# 브레인스토밍: 기존 개선 + 앞으로의 과제

---

## 1. 기존 코드에서 바꿀 것

### 1-1. LLM 호출 구조 (`llm.py`)

**현재 문제:** `generate(question, papers)`가 매번 단일 user 메시지만 보냄. 이전 대화가 전혀 전달되지 않음.

```python
# 현재: 매번 새 대화
messages=[{"role": "user", "content": user_message}]
```

**바꿔야 할 것:**
- `messages` 리스트에 이전 대화 히스토리를 누적해서 전달
- 히스토리가 길어지면 토큰 제한에 걸림 → 요약 전략 또는 슬라이딩 윈도우 필요
- system prompt에 "이전 대화를 참고하라"는 지시 추가

---

### 1-2. 챗봇 루프 (`chatbot.py`)

**현재 문제:** while 루프에서 질문 → 검색 → 답변 → 끝. 상태가 없음.

**바꿔야 할 것:**
- 대화 히스토리 리스트 관리 (`[{role, content}, ...]`)
- 이전 대화 기반으로 검색 쿼리를 보강할지 판단 (query rewriting)
- "아까 그 논문" 같은 참조를 해석할 수 있어야 함

---

### 1-3. 프로젝트 구조

**현재 문제:** `sys.path.insert` 해킹으로 import 처리. 스크립트 간 경로 의존성이 깨지기 쉬움.

```python
# 현재: 각 파일마다 이런 코드
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

**바꿔야 할 것:**
- 패키지 구조로 정리 (`__init__.py`, `pyproject.toml` 또는 `setup.py`)
- 상대 import 또는 패키지 install (`pip install -e .`)로 전환

---

### 1-4. 프롬프트 설계 (`config.py`)

**현재 문제:** 프롬프트가 단일 턴 Q&A에 최적화. 멀티턴 지시가 없음.

**바꿔야 할 것:**
- 멀티턴 대화를 위한 system prompt 보강
- "이전 대화에서 언급된 논문을 참조할 수 있다" 등의 지시
- 답변 언어 설정 (한국어/영어 선택 가능)

---

### 1-5. 모델 선택

**현재:** Claude Haiku (가볍고 빠르지만 추론 능력 제한적)

**고려할 것:**
- 복잡한 질문에는 Sonnet 급이 필요할 수 있음
- config에서 모델 교체가 쉬우니 당장은 괜찮지만, 용도별 모델 분리도 가능
  - 가벼운 질문 → Haiku, 복잡한 분석 → Sonnet

---

### 1-6. 검색 품질

**현재:** L2 distance 기반 시맨틱 검색만 사용. Abstract 1500자 잘림.

**바꿀 수 있는 것:**
- Cosine similarity로 전환 (정규화된 비교)
- Abstract 전문 활용 또는 chunking 전략
- 검색 결과에 MeSH terms 활용한 필터링

---

## 2. 앞으로의 과제

### 2-1. 🔴 대화 메모리 (Memory)

가장 핵심. 없으면 "챗봇"이 아니라 "검색엔진"임.

**선택지:**
| 방식 | 설명 | 장점 | 단점 |
|------|------|------|------|
| Buffer Memory | 최근 N턴 대화를 그대로 전달 | 구현 간단 | 토큰 소모 큼 |
| Summary Memory | 이전 대화를 LLM이 요약해서 유지 | 토큰 절약 | 요약 시 정보 손실 |
| Sliding Window | 최근 K턴 + 오래된 건 요약 | 균형적 | 구현 복잡도 중간 |

**추천:** Buffer Memory로 시작 → 필요 시 Sliding Window로 확장

---

### 2-2. 🔴 멀티턴 대화 지원

메모리와 연결되지만 별도 과제:
- **Query Rewriting**: "그 논문에서 collagen 관련 내용은?" → LLM이 "이전에 검색된 PMID:XXX 논문의 collagen 관련 내용"으로 재작성
- **검색 스킵 판단**: 이전 검색 결과로 충분히 답할 수 있으면 재검색 불필요
- **대화 문맥 참조**: 이전 턴의 논문/답변을 자연스럽게 이어서 활용

---

### 2-3. 🟡 스트리밍 응답

**현재:** 답변 전체가 생성될 때까지 대기 → 사용자 경험 나쁨

**할 일:**
- Claude API `stream=True` 활용
- 토큰 단위로 실시간 출력
- CLI에서도 가능, Web UI에서는 필수

---

### 2-4. 🟡 Web UI

**선택지:**
| 프레임워크 | 장점 | 단점 |
|-----------|------|------|
| Streamlit | 가장 빠른 프로토타입 | 커스텀 제한 |
| Gradio | 챗봇 UI 내장 | 디자인 자유도 낮음 |
| FastAPI + React | 완전한 커스텀 | 개발 비용 높음 |

**추천:** Gradio `ChatInterface`로 시작 (챗봇 특화, 스트리밍 지원 내장)

---

### 2-5. 🟡 Re-ranking

**현재:** 임베딩 유사도 순서 그대로 사용

**개선:**
- Cross-encoder re-ranker 도입 (query-document 쌍을 직접 스코어링)
- Top-K를 넉넉히 가져온 후 re-rank해서 최종 Top-N 선정
- 모델 예시: `cross-encoder/ms-marco-MiniLM-L-6-v2` 또는 바이오메디컬 특화 모델

---

### 2-6. 🟢 Hybrid Search

시맨틱 검색 + 키워드 검색 결합:
- BM25 (키워드) + PubMedBERT (시맨틱) 점수를 가중 합산
- "collagen peptide" 같은 정확한 용어는 키워드가 더 정확
- 일반적 질문은 시맨틱이 더 정확
- ChromaDB 자체로는 어려움 → 별도 BM25 인덱스 필요

---

### 2-7. 🟢 평가 체계

만든 다음 "잘 됐는지" 확인:
- **Retrieval**: 테스트 질문 세트 → 기대 논문이 Top-K에 포함되는지 (Hit Rate, MRR)
- **답변 품질**: 환각 비율, 인용 정확도, 답변 완결성
- **사용자 피드백**: thumbs up/down 수집 (UI 필요)

---

## 3. 요약: 로드맵 순서

```
Phase 1 — 대화가 되게 만들기
  ├─ 대화 메모리 (Buffer Memory)
  ├─ 멀티턴 지원 (히스토리 전달)
  ├─ 프롬프트 개선
  └─ 스트리밍 응답

Phase 2 — 쓸 만하게 만들기
  ├─ Web UI (Gradio)
  ├─ Re-ranking
  └─ 프로젝트 구조 정리

Phase 3 — 잘 되는지 확인하기
  ├─ 평가 체계
  ├─ Hybrid Search
  └─ 모델 최적화
```
