"""LLM Module — Claude or Gemini backend

Assembles context from retrieved papers and generates an answer.
Backend is selected via config.LLM_BACKEND ("claude" or "gemini").
"""
import sys
from pathlib import Path

# ── Config import ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    LLM_BACKEND, CLAUDE_MODEL, CLAUDE_MAX_TOKENS,
    GEMINI_MODEL, GEMINI_MAX_TOKENS,
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CONTEXT_TEMPLATE,
)


def _build_prompt(question, papers):
    """Build context + user message from retrieved papers."""
    context_parts = []
    for i, p in enumerate(papers, 1):
        context_parts.append(CONTEXT_TEMPLATE.format(
            i=i,
            pmid=p["pmid"],
            year=p["year"],
            journal=p["journal"],
            title=p["title"],
            abstract=p["abstract"][:1500],
        ))
    context = "\n".join(context_parts)
    return USER_PROMPT_TEMPLATE.format(context=context, question=question)


class ClaudeLLM:
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = CLAUDE_MODEL
        print(f"LLM ready (Claude: {self.model})")

    def generate(self, question, papers):
        import anthropic
        user_message = _build_prompt(question, papers)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except anthropic.AuthenticationError:
            return "[Error] Invalid API key. Check ANTHROPIC_API_KEY."
        except anthropic.BadRequestError as e:
            return f"[Error] {e}"
        except anthropic.APIError as e:
            return f"[Error] {e}"


class GeminiLLM:
    def __init__(self):
        from google import genai
        self.client = genai.Client()  # reads GOOGLE_API_KEY or GEMINI_API_KEY from env
        self.model = GEMINI_MODEL
        print(f"LLM ready (Gemini: {self.model})")

    def generate(self, question, papers):
        user_message = _build_prompt(question, papers)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_message}"
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return response.text
        except Exception as e:
            return f"[Error] Gemini: {e}"


def create_llm(backend=None):
    """Factory: create the appropriate LLM backend."""
    backend = backend or LLM_BACKEND
    if backend == "gemini":
        return GeminiLLM()
    else:
        return ClaudeLLM()


# Convenience: default export
LLM = create_llm
