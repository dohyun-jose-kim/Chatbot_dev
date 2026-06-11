# ver2.0.1 검증 결과

성공 기준 시나리오: Q1 "What bioactivities does fish scale collagen have?" →
Q2 "What about **its** antioxidant effects?" (대명사 추적).

## 멀티턴 (대명사 추적) — 통과

| 모델 | Q2 standalone 재작성 | 'its' 해소 |
|---|---|---|
| gemma3:4b | "Fish scale collagen exhibits antioxidant effects." (평서문) | ✅ |
| gemma4:31b | "Does fish scale collagen have antioxidant effects?" (의문문, 더 자연스러움) | ✅ |

두 모델 모두 대화기록으로 "its"→"fish scale collagen" 해소, Q2에서 antioxidant 관련
논문으로 검색 전환됨. history-aware retriever 정상 동작.

## 답변 품질 / 인용 정확성

- **gemma4:31b이 더 충실(faithful)**: 검색된 논문에 fish scale collagen의 생리활성
  정보가 실제로 없자 "제공된 논문에 정보 없음"이라고 정직하게 답하고, 근거 있는 PMID만
  인용. RAG의 바람직한 동작.
- **gemma3:4b은 과잉 주장 경향**: 느슨하게 관련된 논문(예: 맹그로브 잎 추출물)을 끌어와
  생리활성이 있는 것처럼 서술. 개발/디버깅엔 빠르지만 품질 판단엔 부적합.
- 데이터 관찰: 코퍼스에 "fish scale collagen 생리활성"을 직접 다룬 논문이 부족해
  retriever가 느슨한 논문을 가져옴. 31b는 이를 정직하게 드러냄(버그 아님, 데이터 특성).

## 턴당 소요시간 (gemma4:31b, Apple Silicon MPS)

| 단계 | 시간 |
|---|---|
| 체인 로드 | 1.8s |
| Q1 (검색+답변) | 68.5s |
| Q2 질문 재작성 | 9.8s |
| Q2 답변 | 58.0s |

후속 턴 = 재작성(~10s) + 답변(~58s) ≈ **턴당 60~70초**. 대화형으로는 느림.
→ 개발은 gemma3:4b, 품질 확인만 gemma4:31b 라는 2-모델 전략이 타당함을 확인.

## 결론

ver2.0.1 목표(멀티턴 + LangChain + Ollama) 달성. 6단계 모두 통과.
속도가 관건이면 추후 질문 재작성만 작은 모델로 분리하는 2-모델 체인 고려 가능(PLAN 리스크 참조).
