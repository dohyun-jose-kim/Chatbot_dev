# PROVENANCE — A: PubMed RAG QA System

## CV 매핑
- CV 항목: Project A (Headline)
- CV 표현 (영문): Project A.  PubMed Literature QA System (RAG-based)
- CV 표현 (한글): Project A.  PubMed 문헌 QA 시스템 (RAG 기반)

## 원본 (회사 GitLab, read-only)
- ifc_ojt_dh.kim/week_7/RAG_Pipeline/

- 복사 일시: 2026-05-04 17:00:31 KST
- 복사 명령: cp -Rp $SRC/week_7/RAG_Pipeline $DST/A_RAG-QA-System/

## 포함 내용
- 3-stage CLI pipeline: 01_embedding (PubMedBERT mean-pool, 768-dim), 02_vectordb (ChromaDB L2), 03_chatbot (Claude Haiku, PMID-grounded)
- data/2026-03-수산부산데이터_screened.csv (5,590 papers; 머지 시 overwrite 방지 위해 리네임됨)
- outputs/01_embedding/embeddings.npy (+ 분할 1of3/2of3/3of3), outputs/02_vectordb/chroma_db/ 포함 (큰 산출물 포함 정책)
- Docs/ 9개: overview-technical, overview-nontechnical, total-act, 01~03 module docs, requirements, logs/

## 머지 — compact-RAG-Chatbot 흡수 (2026-05-06)
원본: `ifc_ojt_dh.kim/week_8/temp/compact-RAG-Chatbot/` (Apr 19, RAG_Pipeline 의 portable 재포장 + 0단계 확장; 0단계 e2e 검증은 미실시)

검증 결과 (md5 byte 단위 동일):
- `chroma.sqlite3`, `embeddings.npy`, `data/screened.csv` 모두 RAG_Pipeline 에서 그대로 복사된 것 → 의미 충돌 없음
- 핵심 코드 (`01/02/03`, `config.py`, `requirements.txt`, `Docs/01~03`) 모두 동일 또는 거의 동일

머지 처리:
- **0단계 (`00_collect/`, `00_preprocess/`, `00_screening/`)** ← compact 에서 RAG_Pipeline 으로 이식 (코드만 추가, 산출물 없음)
- **`run_all.sh`** ← compact 의 portable venv 판으로 교체 (RAG_Pipeline 의 hardcode 절대경로는 다른 머신에서 작동 불가)
- **`README.md`** ← compact 의 "Portable + 0단계" 판이 primary
- **`README_preserved.md`** ← RAG_Pipeline 의 원래 "수산부산물 작업본" README 보존
- **`data/screened.csv` → `data/2026-03-수산부산데이터_screened.csv`** 리네임. 새 도메인 적용 시 0단계가 `data/screened.csv` 를 새로 쓰더라도 기존 5,590편 데이터는 보존됨.
- `_external_repackaging/compact-RAG-Chatbot/` 폴더 자체는 머지 후 제거 (의미 잃음)

## 흡수 완료 — _origin_wk4_screening 도 RAG_Pipeline 으로 머지 (2026-05-06)
원본: `ifc_ojt_dh.kim/week_6/90_NLP_Advancement-week_4/` (의미는 A 의 upstream — 5,590편 코퍼스 생성 코드)

머지 처리:
- `llm_screen.py` (211 줄, Ollama gemma3:4b) → `RAG_Pipeline/00_screening/llm_screen.py` (keyword 다음 1.5단계)
- `docs/01_llm_screening_ollama.md` → `RAG_Pipeline/Docs/00_screening_llm_ollama.md`
- `docs/Progress.md` → `RAG_Pipeline/Docs/_history/Progress_wk4.md`
- `plan1-20260327.md`, `Plan2-00.md` → `RAG_Pipeline/Docs/_history/plan1-wk4.md`, `Plan2-wk4.md`
- `outputs/screened_llm.csv` (30 행 샘플) → `RAG_Pipeline/data/2026-03-수산부산데이터_screened_llm_sample.csv`

드롭 (lineage 만 메모):
- `01_screening/keyword_screen.py` (167 줄) — compact 의 발전판 (`RAG_Pipeline/00_screening/keyword_screen.py`, 163 줄, self-contained 경로) 이 이미 있음. 원본은 `week_4/Task1/Task1-v3/02_paper-list_preprocessing/results_final.csv` 외부 의존이라 portable 패키지에 부적합.

제외 (이전에 검토 후 처음부터 가져오지 않음):
- `02_embedding/embed_pubmedbert.py` → A/01_embedding/embed.py 가 발전판
- `03_vectordb/build_chromadb.py` → A/02_vectordb/build_db.py 가 발전판
- `outputs/screened.csv` (5,591 행) → A/data/2026-03-수산부산데이터_screened.csv 와 동일

⚠ `llm_screen.py` 는 e2e 에서 실제 미실행 — chroma_db 는 keyword 만으로 5,590편 가진 결과. 옵션 단계로 패키지에 포함됨.

## 발전 방향 (사용자 메모용)


## 흡수 대상
- dohyun-jose-kim/03_Chatbot-RAG-LLM/ (이미 발전 베이스 존재)
