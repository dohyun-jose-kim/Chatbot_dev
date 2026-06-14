"""MCP server (spin-off v2.6.0-mcp) — exposes the two search tools over MCP (stdio).

ver2.6.0의 02_chain/tools.py(`search_local_corpus` + `search_pubmed_live`)를 무수정 재사용해
임의의 MCP 클라이언트(Claude Desktop/Code 등)에 두 검색 tool을 노출한다. LLM은 클라이언트 쪽.

NN_ 폴더는 import가 안 되므로 진입점인 여기서만 각 스테이지를 sys.path에 등록한다
(04_interface/chat.py 패턴). 기존 @tool 객체는 .invoke("query")로 호출.

Run (stdio): ../.venv/bin/python 07_mcp/server.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [ROOT, ROOT / "01_retrieval", ROOT / "02_chain"]:
    sys.path.insert(0, str(p))

from mcp.server.fastmcp import FastMCP
from tools import search_local_corpus as _local, search_pubmed_live as _live

mcp = FastMCP("fishery-rag")


@mcp.tool()
def search_local_corpus(query: str) -> str:
    """Search the curated local corpus of 5,590 PubMed abstracts on fishery-byproduct
    bioactivity. Try this FIRST for domain questions. Returns the most relevant papers
    with PMID, year, journal, title, abstract."""
    return _local.invoke(query)


@mcp.tool()
def search_pubmed_live(query: str) -> str:
    """Search PubMed live across the entire database (beyond the local corpus) for recent or
    broader literature. Use when the local corpus lacks relevant papers or the user wants the
    latest findings. Returns up to 5 papers with PMID, title, abstract."""
    return _live.invoke(query)


if __name__ == "__main__":
    mcp.run()  # stdio transport
