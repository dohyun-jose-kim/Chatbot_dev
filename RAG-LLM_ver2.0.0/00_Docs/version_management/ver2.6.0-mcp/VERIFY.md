# ver2.6.0-mcp.1 검증 결과

스핀오프: v2.6.0의 `02_chain/tools.py` 2개 tool을 **MCP 서버(stdio)**로 노출.
성공 기준: V0(deps) · V1(등록) · V2(로컬) · V3(라이브) + V4(클라이언트 수동).

검증 방식: 서브프로세스 대신 FastMCP **in-process** `list_tools()`/`call_tool()`로 프로토콜
계층까지 자동 확인(V1–V3). 실제 클라이언트 등록(V4)은 수동 스모크.

## V0 — deps

| 항목 | 결과 |
|---|---|
| `pip install "mcp>=1.0"` | ✅ `mcp 1.27.2` |
| `from mcp.server.fastmcp import FastMCP` | ✅ import OK |

## V1 — tool 등록 (`list_tools`)

| tool | 입력 스키마 | 설명 |
|---|---|---|
| `search_local_corpus` | `{query: str}` | curated local corpus of 5,590 PubMed abstracts … |
| `search_pubmed_live` | `{query: str}` | live search over the entire PubMed database … |

→ 2개 tool 정확히 노출, 단일 `query` 인자 스키마 + docstring 전달 확인.

## V2 / V3 — 동작 (`call_tool`)

| 검증 | 질의 | 결과 |
|---|---|---|
| **V2** 로컬 | `search_local_corpus("shrimp shell chitosan antimicrobial activity")` | 5,450자, PMID 포함(37295482 등 — 2.6.0 코퍼스와 동일) |
| **V3** 라이브 | `search_pubmed_live("fish collagen peptide antioxidant")` | 6,654자, PMID 포함(42270250 등, 코퍼스 밖 최신) |

`.invoke("query")`(단일 인자 StructuredTool) 경로 확정. PubMedBERT 첫 로드(~500MB)는
`lru_cache`로 1회만 — 첫 V2 호출에 포함됨(정상).

## V4 — 클라이언트 등록 (수동)

`07_mcp/README.md`의 `claude mcp add` / Claude Desktop JSON 스니펫으로 등록 → 도구 목록에
`search_local_corpus`·`search_pubmed_live` 노출 확인. ⏳ 실 클라이언트 스모크는 수동 잔여.

## 재현

```bash
../.venv/bin/python 07_mcp/server.py   # stdio 대기 (클라이언트가 기동)
```
in-process 검증 스크립트는 `mcp.list_tools()` / `mcp.call_tool(name, {"query": ...})` 사용.

## 결론

스핀오프 목표(검색 tool 2개를 MCP로 노출, 방향 A·stdio) 달성. V0–V3 자동 통과,
V4 수동 스모크만 잔여 후 `tag v2.6.0-mcp.1` 권장.

알려진 wart: 검색 시 `chroma.sqlite3`가 modified 표시 → 실행 후 `git restore`, 커밋 금지(2.2.0~).
