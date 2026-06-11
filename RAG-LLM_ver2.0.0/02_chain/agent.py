"""Tool-calling 에이전트 (ver2.6.0)

고정 RAG 체인(rag_chain.py)을 대체한다. LangChain v1 `create_agent` + 2개 tool +
`SqliteSaver` 체크포인터. 멀티턴은 thread_id별 체크포인터가 관리하므로 질문 재작성
체인이 불필요(에이전트가 대화기록을 보고 검색 쿼리를 스스로 형성).

진입점(chat.py/main.py)에서 01_retrieval·02_chain·03_memory를 sys.path에 등록한다.
"""
import re
import sqlite3
from pathlib import Path

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver

from config import LLM_MODEL, AGENT_SYSTEM_PROMPT
from tools import search_local_corpus, search_pubmed_live

_CKPT_DB = str(Path(__file__).resolve().parent.parent / "03_memory" / "agent_checkpoints.db")
TOOLS = [search_local_corpus, search_pubmed_live]


def _checkpointer():
    conn = sqlite3.connect(_CKPT_DB, check_same_thread=False)  # FastAPI 멀티스레드 대응
    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def get_agent(model: str = LLM_MODEL):
    """모델별 tool-calling 에이전트를 생성. 호출측에서 모델별 1회 캐시 권장."""
    llm = ChatOllama(model=model, temperature=0)
    return create_agent(llm, TOOLS, system_prompt=AGENT_SYSTEM_PROMPT,
                        checkpointer=_checkpointer())


def _current_turn(messages):
    """마지막 HumanMessage 이후 메시지(이번 턴의 tool 호출·답변)만 추출.
    체크포인터는 thread 전체 누적 메시지를 반환하므로 현재 턴만 분리한다."""
    start = 0
    for i, m in enumerate(messages):
        if type(m).__name__ == "HumanMessage":
            start = i
    return messages[start:]


def extract_steps(messages) -> list[dict]:
    """이번 턴의 tool 호출(이름·쿼리)을 추출 — UI/CLI 노출용."""
    steps = []
    for m in _current_turn(messages):
        for tc in getattr(m, "tool_calls", None) or []:
            steps.append({"tool": tc["name"], "query": tc.get("args", {}).get("query", "")})
    return steps


def extract_pmids(messages) -> list[str]:
    """이번 턴 tool 결과(ToolMessage)에서 인용된 PMID를 순서 유지·중복 제거로 추출."""
    seen, out = set(), []
    for m in _current_turn(messages):
        if type(m).__name__ == "ToolMessage":
            for pid in re.findall(r"PMID:\s*(\d+)", m.content or ""):
                if pid not in seen:
                    seen.add(pid)
                    out.append(pid)
    return out
