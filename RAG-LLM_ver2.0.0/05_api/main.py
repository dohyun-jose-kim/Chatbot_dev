"""FastAPI backend — POST /chat

references/conversational-rag-chatbot api/main.py 차용.
OpenAI 제거, 체인을 모델별 1회 로드해 캐시(요청마다 PubMedBERT 재로드 방지),
문서 업로드 엔드포인트 제거, 응답에 검색 PMID 포함.

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
from rag_chain import get_rag_chain
from db_utils import insert_application_logs, get_chat_history

app = FastAPI(title="Fishery Byproduct RAG API")


@lru_cache(maxsize=4)
def cached_chain(model: str):
    """모델별 체인 1회 로드 후 재사용 (PubMedBERT/Ollama 재로드 방지)."""
    return get_rag_chain(model)


@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    model = query_input.model.value

    chat_history = get_chat_history(session_id)
    out = cached_chain(model).invoke({
        "input": query_input.question,
        "chat_history": chat_history,
    })
    answer = out["answer"]
    pmids = [d.metadata["pmid"] for d in out["context"]]

    insert_application_logs(session_id, query_input.question, answer, model)
    return QueryResponse(answer=answer, session_id=session_id, model=query_input.model, pmids=pmids)
