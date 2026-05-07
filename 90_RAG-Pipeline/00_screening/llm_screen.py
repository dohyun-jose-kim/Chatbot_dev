"""
1.5단계: LLM 분야 판정 (Ollama)

키워드 스크리닝을 통과한 논문의 abstract를 로컬 LLM에게 보내
수산부산물 기능성 연구 분야에 적합한지 판정한다.

사전 준비:
    brew install ollama
    ollama serve          # 서버 시작 (별도 터미널)
    ollama pull gemma3:4b # 모델 다운로드

입력: outputs/screened.csv
출력: outputs/screened_llm.csv (is_relevant, llm_reason 컬럼 추가)
"""

import json
import os
import sys
import time

import pandas as pd
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "..", "outputs", "screened.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "..", "outputs", "screened_llm.csv")
PROGRESS_CSV = os.path.join(SCRIPT_DIR, "..", "outputs", "screened_llm_progress.csv")

# ── Ollama 설정 ──
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:1b"
SAMPLE_LIMIT = 30  # 0이면 전체 처리, 양수면 해당 건수만 처리

# ── 프롬프트 ──
SYSTEM_PROMPT = """You are a biomedical literature screening assistant.
Your task: determine if a paper is relevant to research on
**bioactive compounds derived from fishery/aquatic byproducts**.

A paper is RELEVANT if it studies:
- Functional/bioactive properties (antioxidant, anti-inflammatory, antimicrobial, etc.)
- From compounds extracted from marine/aquatic organisms
- Specifically from byproducts or processing waste (bone, skin, shell, viscera, scale, head, etc.)

A paper is NOT RELEVANT if:
- It studies aquatic organisms but NOT their byproducts (e.g., whole fish nutrition)
- It studies byproducts but NOT bioactivity (e.g., waste management, feed formulation only)
- The organism is terrestrial (e.g., chicken, bovine) even if keywords overlap
- It is purely about aquaculture/farming without bioactivity focus

Respond in this exact JSON format:
{"relevant": true/false, "reason": "one sentence explanation"}
"""

USER_PROMPT_TEMPLATE = """Title: {title}
Abstract: {abstract}
MeSH Terms: {mesh_terms}

Is this paper about bioactive compounds from fishery byproducts?"""


MAX_RETRIES = 3
TIMEOUT = 300  # 초


def call_ollama(prompt: str) -> dict:
    """Ollama API 호출. 타임아웃 시 재시도. {"relevant": bool, "reason": str} 반환."""
    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # 일관된 판정을 위해 낮은 temperature
            "num_predict": 150,  # 짧은 응답만 필요
        },
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()

            # JSON 파싱 시도
            # LLM이 ```json ... ``` 감싸는 경우 처리
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
                if not text:
                    text = resp.json().get("response", "").strip()
                    text = text.split("```")[-2].strip()

            result = json.loads(text)
            return {
                "relevant": bool(result.get("relevant", False)),
                "reason": str(result.get("reason", "")),
            }
        except (json.JSONDecodeError, KeyError):
            # JSON 파싱 실패 시 텍스트에서 YES/NO 추출
            raw = resp.json().get("response", "").upper()
            if "TRUE" in raw or "YES" in raw or '"RELEVANT": TRUE' in raw:
                return {"relevant": True, "reason": "(parsed from text)"}
            return {"relevant": False, "reason": f"(parse failed: {raw[:80]})"}
        except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
            wait = 5 * (attempt + 1)
            print(f"\n  타임아웃 (시도 {attempt+1}/{MAX_RETRIES}) — {wait}초 후 재시도")
            time.sleep(wait)
        except requests.ConnectionError:
            print("\n  ERROR: Ollama 서버에 연결할 수 없습니다.")
            print("  'ollama serve' 를 실행했는지 확인해주세요.")
            sys.exit(1)

    # 모든 재시도 실패
    return {"relevant": False, "reason": "(timeout after retries)"}


def screen_abstract(title: str, abstract: str, mesh_terms: str) -> dict:
    """단일 논문의 분야 적합성을 LLM으로 판정."""
    prompt = USER_PROMPT_TEMPLATE.format(
        title=title or "",
        abstract=abstract or "",
        mesh_terms=mesh_terms or "",
    )
    return call_ollama(prompt)


def main():
    print("=" * 60)
    print("1.5단계: LLM 분야 판정 (Ollama)")
    print(f"모델: {MODEL}")
    print("=" * 60)

    df = pd.read_csv(INPUT_CSV)
    total_all = len(df)

    # 샘플 제한
    if SAMPLE_LIMIT > 0:
        df = df.head(SAMPLE_LIMIT)
        print(f"  전체 논문 수: {total_all:,} → 샘플 {SAMPLE_LIMIT}편만 처리")
    else:
        print(f"  입력 논문 수: {total_all:,}")

    total = len(df)
    results = []

    # 처리
    start_time = time.time()
    try:
        for i in range(total):
            row = df.iloc[i]
            result = screen_abstract(
                title=row.get("title", ""),
                abstract=row.get("abstract", ""),
                mesh_terms=row.get("mesh_terms", ""),
            )
            results.append({
                "is_relevant": result["relevant"],
                "llm_reason": result["reason"],
            })

            # 진행 상황 출력
            elapsed = time.time() - start_time
            done = i + 1
            speed = done / elapsed if elapsed > 0 else 0
            remaining = (total - done) / speed if speed > 0 else 0
            relevant_count = sum(1 for r in results if r["is_relevant"])

            print(
                f"  [{done:,}/{total:,}] "
                f"적합: {relevant_count:,} | "
                f"속도: {speed:.1f}건/초 | "
                f"남은 시간: {remaining/60:.1f}분",
                end="\r",
            )

    except KeyboardInterrupt:
        print(f"\n\n  중단됨! {len(results):,}건까지 저장합니다.")

    # 최종 저장
    print()
    df = df.iloc[: len(results)].copy()
    df["is_relevant"] = [r["is_relevant"] for r in results]
    df["llm_reason"] = [r["llm_reason"] for r in results]
    df["manual_check"] = ""  # 수동 판정 컬럼 (직접 작성용)

    relevant_count = df["is_relevant"].sum()
    print(f"\n  LLM 적합 판정: {relevant_count:,} / {len(df):,}")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  저장: {OUTPUT_CSV}")
    print(f"  → 'manual_check' 컬럼에 직접 판정 결과를 기입해주세요.")

    # 진행 파일 정리
    if os.path.exists(PROGRESS_CSV):
        os.remove(PROGRESS_CSV)
        print("  진행 파일 삭제")

    elapsed_total = time.time() - start_time
    print(f"  소요 시간: {elapsed_total/60:.1f}분")


def _save_progress(df: pd.DataFrame, results: list[dict]):
    """중간 진행 상태를 저장."""
    n = len(results)
    progress = df.iloc[:n].copy()
    progress["is_relevant"] = [r["is_relevant"] for r in results]
    progress["llm_reason"] = [r["llm_reason"] for r in results]
    progress.to_csv(PROGRESS_CSV, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
