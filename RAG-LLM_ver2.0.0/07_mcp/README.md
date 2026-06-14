# 07_mcp — MCP 서버 (스핀오프 v2.6.0-mcp)

동봉 코퍼스(5,590편) + PubMed 라이브 검색을 **MCP 서버**로 노출한다. Claude Desktop/Code 등
**임의의 MCP 클라이언트**가 두 검색 tool을 직접 쓴다 — LLM은 **클라이언트 쪽**에 있다.

| tool | 동작 |
|---|---|
| `search_local_corpus(query)` | 동봉 chroma 코퍼스(PubMedBERT 임베딩) 조회 → PMID·연도·저널·제목·초록 |
| `search_pubmed_live(query)` | Entrez로 PubMed 전체 라이브 검색 → 최신·광범위 문헌 PMID |

`02_chain/tools.py`의 `@tool`을 무수정 재사용한다(검색 로직 재구현 없음). 메인 vX.Y.Z
라인과 독립이며 2.4.0(인증)·2.5.0(배포)에 의존하지 않는다.

## 실행 (stdio)

```bash
../.venv/bin/python 07_mcp/server.py
```
클라이언트가 이 명령으로 서버를 자식 프로세스로 띄운다. 직접 실행하면 stdio 대기 상태가 된다.
첫 `search_local_corpus` 호출 시 PubMedBERT(~500MB)를 1회 로드하므로 첫 응답은 느릴 수 있다.

## 클라이언트 등록

경로는 절대경로로 — `<REPO>`는 이 저장소 루트의 절대경로.

### Claude Code
```bash
claude mcp add fishery-rag -- <REPO>/.venv/bin/python <REPO>/RAG-LLM_ver2.0.0/07_mcp/server.py
```

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "fishery-rag": {
      "command": "<REPO>/.venv/bin/python",
      "args": ["<REPO>/RAG-LLM_ver2.0.0/07_mcp/server.py"]
    }
  }
}
```

등록 후 클라이언트 도구 목록에 `search_local_corpus`·`search_pubmed_live`가 노출되면 성공.

## 환경변수 (선택)

`search_pubmed_live`의 레이트 리밋 완화 — 미설정이어도 동작한다.
```bash
export NCBI_EMAIL="you@example.com"   # 권장
export NCBI_API_KEY="..."             # 선택 (3→10 req/s)
```

## 범위

stdio·로컬·단일 사용자만 다룬다. 에이전트 전체를 단일 tool로 노출(Ollama 생성 포함)하거나
HTTP/원격 전송이 필요하면 별도 가지로 분리한다.
