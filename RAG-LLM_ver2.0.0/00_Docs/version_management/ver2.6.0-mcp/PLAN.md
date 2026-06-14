# ver2.6.0-mcp.1 — MCP 서버화 (검색 tool 노출) 구현 계획

> **스핀오프** (메인 vX.Y.Z 라인 밖). base: **v2.6.0**의 `02_chain/tools.py` 재사용.
> 태그 네임스페이스 `v2.6.0-mcp.N`, 문서 `ver2.6.0-mcp/`. 메인 2.4.0(인증)·2.5.0(배포)과
> **의존성 없음** — 2.6.0 직후 아무 때나 가능한 독립 가지.

## 목표

동봉 코퍼스(5,590편) + PubMed 라이브 검색을 **MCP 서버**로 노출해, Claude Desktop/Code 등
**임의의 MCP 클라이언트**가 두 검색 tool을 직접 쓰게 한다. LLM은 **클라이언트 쪽**에 있다.

- **노출 범위**: `search_local_corpus` + `search_pubmed_live` 2개 tool (방향 A)
- **전송**: **stdio** (로컬 단일 사용자, 클라이언트가 서버 프로세스를 직접 기동)
- **재사용**: `02_chain/tools.py`의 `@tool` 함수를 `.invoke()`로 호출 — 검색 로직 재구현 없음
- 에이전트/Ollama 생성은 **포함하지 않음** (그건 방향 B, 추후 한 줄로 얹을 수 있음)

```
Claude Desktop/Code ─MCP(stdio)─→ [07_mcp/server.py]
   (LLM = 클라이언트)                ├ search_local_corpus → 01_retrieval → chroma_db(5,590편)
                                     └ search_pubmed_live  → Entrez → PubMed 전체
```

**성공 기준 (검증 시나리오)**
```
V0 deps:   `import mcp` 성공, FastMCP import OK
V1 등록:   서버가 tool 2개를 노출 (list_tools → search_local_corpus, search_pubmed_live)
V2 로컬:   call_tool("search_local_corpus", {"query": "shrimp shell chitosan antimicrobial"})
           → 코퍼스 PMID 포함 텍스트
V3 라이브: call_tool("search_pubmed_live", {"query": "fish collagen peptide antioxidant"})
           → PubMed PMID 포함 텍스트 (네트워크 에러 시 graceful 메시지)
V4 클라이언트: Claude Code `claude mcp add`로 등록 → 도구 목록에 노출 (수동 스모크)
```

## 빌려오는 것 (직접 구현 최소화)

| 출처 | 가져올 것 | 수정 |
|---|---|---|
| MCP 공식 Python SDK (`mcp`) `FastMCP` | 서버 골격, `@mcp.tool()` 데코레이터, stdio `mcp.run()` | 없음 (표준 패턴) |
| ver2.6.0 `02_chain/tools.py` | `search_local_corpus`·`search_pubmed_live` (검색 로직 전부) | **무수정** — `.invoke(query)`로 호출 |
| ver2.6.0 `04_interface/chat.py` | `NN_` 폴더 `sys.path` 등록 패턴 (진입점에서만) | 그대로 적용 |
| `config.py` | chroma 경로·NCBI 설정 | 그대로 (tools.py가 이미 참조) |

## 핵심 설계 결정

### 1. 새 노출 스테이지 `07_mcp/` (05 API · 06 UI 와 형제)
번호 컨벤션(`01 검색 → 02 에이전트 → 03 기억`, 노출 `05 API → 06 UI`)에 맞춰 MCP 노출을
`07_mcp/server.py` 단일 진입점으로 둔다. `NN_` 폴더는 import 불가하므로 chat.py처럼
진입점에서 `ROOT / 01_retrieval / 02_chain`을 `sys.path`에 등록한다.

### 2. tool 재구현 금지 — 기존 StructuredTool을 얇게 감쌈
`@tool` 객체는 `.invoke("query")`로 호출 가능. FastMCP는 데코레이트된 함수의 시그니처·
docstring으로 스키마를 만들므로, `query: str → str` 래퍼에 docstring을 달고 내부에서
`_local.invoke(query)` 호출. 검색·포맷·에러처리는 전부 tools.py 그대로 재사용.

### 3. stdio 전송 (배포 의존성 차단)
`mcp.run()` 기본 stdio. 클라이언트가 `command: <venv python>, args: [server.py]`로 서버를
자식 프로세스로 띄움. HTTPS/CORS/시크릿 불필요 → 2.5.0 배포 트랙과 분리.
(HTTP 전송이 필요해지면 그때 2.5.0 이후 가지로 분리.)

### 4. 검증은 in-process 우선
서브프로세스 stdio 클라이언트 대신 FastMCP의 `await mcp.list_tools()` /
`await mcp.call_tool(...)`로 프로토콜 계층까지 자동 검증(V1–V3). 실제 클라이언트 등록(V4)은
수동 스모크.

## 파일 구성

```
RAG-LLM_ver2.0.0/
├── requirements.txt          # + mcp (공식 SDK; FastMCP 포함)
├── 07_mcp/                    # (신규) MCP 노출 스테이지
│   ├── server.py             # (신규) FastMCP 서버: 2 tool 래핑 + stdio run
│   └── README.md             # (신규) 클라이언트 등록법(Claude Desktop/Code), 실행
└── 00_Docs/version_management/ver2.6.0-mcp/
    ├── PLAN.md               # (본 문서)
    └── VERIFY.md             # (신규) V0–V4 측정 결과
```
메인 README 로드맵 표에 **스핀오프 행** 1줄 추가.

## 구현 단계 (Phase별)

원칙: 각 Phase는 시스템을 동작 상태로 남긴다. 완료 시 `tag v2.6.0-mcp.1`.

### Phase 0 — deps + 스테이지
- **0.1** `requirements.txt`: `# ver2.6.0-mcp — MCP 서버` 섹션 + `mcp` 추가, 설치
  → verify(V0): `./.venv/bin/python -c "from mcp.server.fastmcp import FastMCP"`

### Phase A — 서버 구현
- **A.1** `07_mcp/server.py`: sys.path 등록 → tools import → `FastMCP("fishery-rag")` +
  `@mcp.tool()` 2개 래퍼 + `mcp.run()`
  → verify(V1): in-process `list_tools()` 가 2개 tool·올바른 스키마 노출

### Phase B — 동작 검증
- **B.1** in-process `call_tool` 로 V2(로컬: PMID 포함)·V3(라이브: PMID 포함/graceful) 확인
  → verify: 두 호출 모두 비어있지 않은 텍스트 + 로컬은 코퍼스 PMID 포함

### Phase C — 문서 + 릴리스
- **C.1** `07_mcp/README.md`: Claude Desktop JSON / `claude mcp add` 등록 스니펫 + stdio 설명
- **C.2** 메인 README 로드맵에 스핀오프 행, `ver2.6.0-mcp/VERIFY.md`(V0–V4)
- **C.3** (수동) V4: 실제 클라이언트 등록 스모크
- **C.4** dev 커밋 → main 머지 → **tag `v2.6.0-mcp.1`**

## 범위 제외
- 에이전트 전체를 단일 tool로 노출(방향 B), Ollama 생성 포함 — 별도
- HTTP/원격 전송, 인증, 멀티 클라이언트 동시성 (stdio 로컬 단일)
- 코퍼스 외 신규 tool(요약·메타분석 등)

## 리스크
- **`mcp` SDK 버전 호환**: FastMCP 위치가 `mcp.server.fastmcp`. 설치 후 import로 확정.
- **`.invoke` 시그니처**: 단일 인자 StructuredTool은 `.invoke("query")` 또는
  `.invoke({"query": ...})`. import 후 1회 확인해 고정.
- **PubMedBERT 첫 로드 지연(~500MB)**: 첫 `search_local_corpus` 호출 시 1회 로드(lru_cache).
  클라이언트 첫 호출이 느릴 수 있음 — 정상.
- **chroma wart**(2.2.0~): 검색 후 `chroma.sqlite3` modified 표시 → 실행 후 `git restore`, 커밋 금지.
- **NN_ import**: 반드시 진입점(server.py)에서만 sys.path 등록(chat.py 패턴 준수).
