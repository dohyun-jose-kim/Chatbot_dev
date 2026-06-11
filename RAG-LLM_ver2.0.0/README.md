# RAG-LLM ver2.0.0 — Multi-turn 대화형 RAG

ver1(`../90_RAG-Pipeline`, "Domain RAG Search Engine")의 stateless Q&A를
**멀티턴 대화형 RAG**로 전환하는 작업. LLM은 로컬 **Ollama**, 프레임워크는 **LangChain**.

ver1의 chroma_db(PubMed 5,590편, PubMedBERT 임베딩)를 **읽기 전용으로 재사용**한다.
수집~DB구축 파이프라인(ver1의 00~02)은 다시 만들지 않는다.

## 버전 로드맵

| 버전 | 내용 | 상태 |
|---|---|---|
| 2.0.1 | Multi-turn + LangChain + Ollama 전환 | 완료 (tag v2.0.1) |
| 2.2.0 | API + UI (FastAPI + Streamlit, 2.3.0 app 흡수) | 완료 (tag v2.2.0) |
| 2.4.0 | user config, id/pw | 예정 |
| 2.5.0 | server deploy | 예정 |
| 2.6.0 | LangGraph 에이전트화 — RAG를 tool로 편입, 멀티 tool 오케스트레이션 | 예정 |

자세한 계획은 [`00_Docs/version_management/ver2.0.1_+Multi-turn+LangChain/PLAN.md`](00_Docs/version_management/ver2.0.1_+Multi-turn+LangChain/PLAN.md),
진행 추적은 GitHub 이슈 [#1](https://github.com/dohyun-jose-kim/Chatbot_dev/issues/1).

## 디렉터리 구조

런타임 흐름이 폴더 번호대로 흐른다: `01 검색 → 02 체인 → 03 기억 → 04 대화`.

```
RAG-LLM_ver2.0.0/
├── config.py                    # 공유 설정: ver1 chroma_db 경로, 모델명, TOP_K, 프롬프트
├── requirements.txt
├── 00_Docs/
│   └── version_management/      # 버전별 계획 문서 (PLAN.md 등)
├── 01_retrieval/
│   └── pubmedbert_retriever.py  # ver1 검색 로직 → LangChain BaseRetriever 어댑터
├── 02_chain/
│   └── rag_chain.py             # 멀티턴 체인: ChatOllama + history-aware retriever
├── 03_memory/
│   └── db_utils.py              # 세션별 대화기록 SQLite
└── 04_interface/
    └── chat.py                  # CLI 멀티턴 루프 (진입점)
```

## 셋업

```bash
# 저장소 루트의 .venv 하나를 ver2.x 전체에서 재사용
../.venv/bin/python -m pip install -r requirements.txt

# Ollama 모델 (이미 받아둔 것 사용)
#   gemma4:31b — 품질 확인용 / gemma3:4b — 개발·디버깅용
ollama list
```

## 실행

```bash
# 진입점에서 실행 (아직 미구현 — 2.0.1 4단계)
python 04_interface/chat.py
```

`NN_` 폴더는 숫자로 시작해 Python `import`가 안 되므로, 진입점에서만 각 스테이지를
`sys.path`에 등록한다. 개발 중 단일 스테이지 테스트는 `PYTHONPATH`로:

```bash
PYTHONPATH=.:01_retrieval ../.venv/bin/python -c "from pubmedbert_retriever import PubMedBERTRetriever; ..."
```

## 주의

- **ver1 동결**: ver1 코드는 import하지 않고 필요한 로직만 복사해온다. chroma_db는 읽기 전용.
- **chroma_db 부작용**: chromadb는 쿼리 시 sqlite를 read-write로 열어 파일이 변경됨으로
  표시될 수 있다. ver1 동결 유지를 위해 그 변경은 커밋하지 않는다
  (`git checkout -- ../90_RAG-Pipeline/.../chroma.sqlite3`). 런타임에는 무해.
