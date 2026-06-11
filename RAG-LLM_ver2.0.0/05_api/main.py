"""FastAPI backend — POST /chat (ver2.6.0 tool-calling agent)

ver2.2.0의 고정 체인을 tool-calling 에이전트로 교체. get_agent를 모델별 1회 로드해
캐시(PubMedBERT/Ollama 재로드 방지). 멀티턴은 thread_id=session_id 체크포인터가 관리하므로
chat_history를 수동 전달하지 않는다. 응답에 검색 PMID + tool 호출(steps) 포함.

NN_ 폴더는 import 불가하므로 여기서 각 스테이지를 sys.path에 등록한다.
실행: uvicorn main:app --app-dir 05_api  (또는 run_app.sh)
"""
import sys
import uuid
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [ROOT, ROOT / "01_retrieval", ROOT / "02_chain", ROOT / "03_memory"]:
    sys.path.insert(0, str(p))

from fastapi import FastAPI
from models import QueryInput, QueryResponse
from agent import get_agent, extract_steps, extract_pmids
from db_utils import insert_application_logs

app = FastAPI(title="Fishery Byproduct RAG Agent API")


@lru_cache(maxsize=4)
def cached_agent(model: str):
    """모델별 에이전트 1회 로드 후 재사용 (PubMedBERT/Ollama 재로드 방지)."""
    return get_agent(model)


@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    model = query_input.model.value

    out = cached_agent(model).invoke(
        {"messages": [("user", query_input.question)]},
        config={"configurable": {"thread_id": session_id}},
    )
    msgs = out["messages"]
    answer = msgs[-1].content

    insert_application_logs(session_id, query_input.question, answer, model)
    return QueryResponse(
        answer=answer, session_id=session_id, model=query_input.model,
        pmids=extract_pmids(msgs), steps=extract_steps(msgs),
    )
