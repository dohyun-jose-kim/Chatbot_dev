"""Multi-turn RAG Chatbot — CLI Interface (진입점)

ver1 03_chatbot/chatbot.py의 CLI UX를 차용하되 멀티턴으로 확장.
세션별 대화기록을 SQLite에 쌓아 history-aware 검색/답변을 수행한다.

Usage:
    python 04_interface/chat.py          # 품질 모델 (gemma4:31b)
    python 04_interface/chat.py --dev    # 개발 모델 (gemma3:4b, 빠름)

NN_ 폴더는 import 불가하므로 진입점에서 각 스테이지를 sys.path에 등록한다.
"""
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [ROOT, ROOT / "01_retrieval", ROOT / "02_chain", ROOT / "03_memory"]:
    sys.path.insert(0, str(p))

from config import LLM_MODEL, DEV_MODEL
from rag_chain import get_rag_chain
from db_utils import insert_application_logs, get_chat_history


def main():
    model = DEV_MODEL if "--dev" in sys.argv else LLM_MODEL

    print("=" * 60)
    print("  Fishery Byproduct Bioactivity — Multi-turn RAG Chatbot")
    print(f"  model: {model}")
    print("  commands: 'new' 새 세션 | 'quit'/'q' 종료")
    print("=" * 60)
    print("\nLoading models...")
    chain = get_rag_chain(model)
    session_id = str(uuid.uuid4())
    print(f"Ready! (session: {session_id[:8]})\n")

    while True:
        try:
            question = input("\nQuery> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("q", "quit", "exit"):
            print("Exiting.")
            break
        if question.lower() == "new":
            session_id = str(uuid.uuid4())
            print(f"  New session: {session_id[:8]}")
            continue

        chat_history = get_chat_history(session_id)
        out = chain.invoke({"input": question, "chat_history": chat_history})
        answer = out["answer"]

        print(f"\n{'─' * 60}")
        print(answer)
        print(f"{'─' * 60}")
        print("  retrieved PMIDs:", ", ".join(d.metadata["pmid"] for d in out["context"]))

        insert_application_logs(session_id, question, answer, model)


if __name__ == "__main__":
    main()
