"""Multi-turn RAG Chatbot — CLI Interface (진입점, ver2.6.0 에이전트)

ver2.2.0의 고정 체인을 tool-calling 에이전트로 교체. 멀티턴은 thread_id=session_id
체크포인터가 관리한다(질문 재작성 체인을 에이전트가 흡수). tool 호출과 PMID를 함께 출력.

Usage:
    python 04_interface/chat.py          # 품질 모델 (gemma4:31b)
    python 04_interface/chat.py --dev    # 개발 모델 (gemma4:26b, 빠름)

NN_ 폴더는 import 불가하므로 진입점에서 각 스테이지를 sys.path에 등록한다.
"""
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [ROOT, ROOT / "01_retrieval", ROOT / "02_chain", ROOT / "03_memory"]:
    sys.path.insert(0, str(p))

from config import LLM_MODEL, DEV_MODEL
from agent import get_agent, extract_steps, extract_pmids
from db_utils import insert_application_logs


def main():
    model = DEV_MODEL if "--dev" in sys.argv else LLM_MODEL

    print("=" * 60)
    print("  Fishery Byproduct Bioactivity — Agentic RAG Chatbot")
    print(f"  model: {model}")
    print("  commands: 'new' 새 세션 | 'quit'/'q' 종료")
    print("=" * 60)
    print("\nLoading agent...")
    agent = get_agent(model)
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

        out = agent.invoke(
            {"messages": [("user", question)]},
            config={"configurable": {"thread_id": session_id}},
        )
        msgs = out["messages"]
        answer = msgs[-1].content
        steps = extract_steps(msgs)
        pmids = extract_pmids(msgs)

        print(f"\n{'─' * 60}")
        print(answer)
        print(f"{'─' * 60}")
        if steps:
            print("  🔧 tools:", "; ".join(f"{s['tool']}('{s['query']}')" for s in steps))
        if pmids:
            print("  PMIDs:", ", ".join(pmids))

        insert_application_logs(session_id, question, answer, model)


if __name__ == "__main__":
    main()
