"""Fishery Byproduct RAG Chatbot — CLI Interface

Queries PubMed papers via ChromaDB + PubMedBERT retrieval,
then generates grounded answers via Claude API.

Usage:
    python 03_chatbot/chatbot.py
    (run from RAG_Pipeline/ directory)
"""
import sys
import time
from pathlib import Path

# ── Config import ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import TOP_K
from retriever import Retriever
from llm import create_llm


def print_banner():
    print("=" * 60)
    print("  Fishery Byproduct Bioactivity — RAG Chatbot")
    print("  PubMed paper-grounded Q&A system")
    print("=" * 60)
    print("  Commands:")
    print("    quit / q       Exit")
    print("    k <number>     Change top-K (default: 5)")
    print("    papers         Show last retrieved papers")
    print("    help           Show this message")
    print("=" * 60)


def main():
    print_banner()

    print("\nLoading models...")
    retriever = Retriever()
    llm_client = create_llm()
    print("Ready!\n")

    top_k = TOP_K
    last_papers = []

    while True:
        try:
            question = input("\nQuery> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue

        # Commands
        if question.lower() in ("q", "quit", "exit"):
            print("Exiting.")
            break

        if question.lower() == "help":
            print_banner()
            continue

        if question.lower().startswith("k "):
            try:
                new_k = int(question.split()[1])
                if 1 <= new_k <= 20:
                    top_k = new_k
                    print(f"  Top-K set to {top_k}")
                else:
                    print("  k must be between 1 and 20")
            except (ValueError, IndexError):
                print("  Usage: k 5")
            continue

        if question.lower() == "papers":
            if not last_papers:
                print("  No papers retrieved yet.")
            else:
                for i, p in enumerate(last_papers, 1):
                    print(f"  [{i}] PMID:{p['pmid']} ({p['year']}) dist={p['distance']:.4f}")
                    print(f"      {p['title'][:80]}")
            continue

        # RAG pipeline
        print(f"\n  Searching (top-{top_k})...")
        t0 = time.time()
        papers = retriever.search(question, top_k=top_k)
        t_search = time.time() - t0

        print(f"  Found {len(papers)} papers ({t_search:.1f}s)")
        for i, p in enumerate(papers, 1):
            print(f"    [{i}] PMID:{p['pmid']} | {p['title'][:60]}...")

        print(f"\n  Generating answer...")
        t0 = time.time()
        answer = llm_client.generate(question, papers)
        t_llm = time.time() - t0

        print(f"\n{'─' * 60}")
        print(answer)
        print(f"{'─' * 60}")
        print(f"  (search {t_search:.1f}s + generation {t_llm:.1f}s)")

        last_papers = papers


if __name__ == "__main__":
    main()
