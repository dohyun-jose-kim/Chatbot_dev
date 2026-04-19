"""
PubMed XML 기반 초록 텍스트 전처리 (preprocess_step1.py)

사용법:
    python preprocess_step1.py diagnose   # 진단만 (데이터 오염 현황 분석)
    python preprocess_step1.py clean      # 전처리 실행 → results_cleaned.csv
    python preprocess_step1.py            # 둘 다 (진단 → 전처리)
"""

import html
import re
import sys
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "..", "00_collect", "results.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "results_cleaned.csv")


# =====================================================================
# 왜 전처리가 필요한가? — PubMed XML에서 흔히 발생하는 4가지 오염 패턴
# =====================================================================
#
# 1. HTML Entity (4건 발견)
#    ─────────────────────
#    원인: PubMed XML 내부에서 특수문자를 entity로 인코딩하여 저장함.
#          EFetch로 XML을 받아 텍스트만 추출하면 entity가 그대로 남음.
#    예시: &amp; → &,  &alpha; → α,  &lt; → <,  &mdash; → —
#    해결: html.unescape()로 디코딩
#
# 2. 특수 유니코드 공백 (2,045건 발견)
#    ──────────────────────────────────
#    원인: PubMed가 숫자와 단위 사이, 수식 표현 등에 thin space(\u2009),
#          non-breaking space(\xa0) 등을 삽입하는 것이 관행임.
#    예시: "P\u2009<\u20090.05" (P < 0.05 사이에 thin space)
#          "10\xa0mg" (숫자와 단위 사이 non-breaking space)
#    해결: 정규식으로 일반 공백(' ')으로 치환
#
# 3. 섹션 라벨 (399건 발견)
#    ──────────────────────
#    원인: Structured abstract 형식의 논문은 XML에서 <AbstractText> 태그에
#          Label="BACKGROUND" 같은 속성이 붙음. 수집 시 이를 텍스트로 합치면
#          "BACKGROUND: ...", "METHODS: ..." 형태로 본문에 라벨이 남음.
#    예시: "BACKGROUND: Yellowfin tuna is... METHODS: We used..."
#    해결: 알려진 라벨 패턴을 정규식으로 제거
#
# 4. 빈 abstract (38건 발견)
#    ───────────────────────
#    원인: 리뷰, 레터, 에디토리얼 등 초록이 없는 논문 유형이 존재함.
#          또는 출판사가 초록을 PubMed에 제공하지 않은 경우.
#    해결: 빈 문자열("")로 통일 (NaN, 공백만 있는 경우 포함)
#
# =====================================================================
# 진단 방법 — 어떻게 이 오염을 찾는가?
# =====================================================================
#
# 각 패턴에 대해 정규식으로 해당 건수를 카운트하고 샘플을 확인한다.
#
#   HTML entity:      r'&[a-z]+;|&#[0-9]+;'
#   특수 공백:         r'[\xa0\u2009\u200b\u2002\u2003...]'
#   섹션 라벨:        r'(BACKGROUND|METHODS|RESULTS|CONCLUSION)S?:'
#   빈 abstract:      pd.isna() 또는 빈 문자열 체크
#
# 이 패턴들은 "PubMed XML 데이터의 알려진 특성"을 기반으로 한다.
# =====================================================================


# ── 전처리 규칙 정의 ──────────────────────────────────────────────

SECTION_LABELS = re.compile(
    r'\b(BACKGROUND|OBJECTIVES?|INTRODUCTION|PURPOSE|AIMS?|SCOPE|'
    r'METHODS?|MATERIALS?|DESIGN|SETTING|PARTICIPANTS?|INTERVENTIONS?|'
    r'RESULTS?|FINDINGS?|OUTCOMES?|'
    r'DISCUSSIONS?|CONCLUSIONS?|SIGNIFICANCE|IMPLICATIONS?|'
    r'UNLABELLED|CONTEXT|RATIONALE|HYPOTHESIS|'
    r'BACKGROUND AND AIMS?|MATERIALS AND METHODS?|'
    r'RESULTS AND DISCUSSIONS?)\s*:\s*',
    re.IGNORECASE
)

SPECIAL_SPACES = re.compile(
    r'[\xa0\u2009\u200b\u2002\u2003\u200a\u2005\u2006\u2007\u2008\u202f\u205f]'
)


# ── 진단 ──────────────────────────────────────────────────────────

def diagnose(df):
    """데이터 오염 현황을 분석하고 출력한다."""
    abstracts = df["abstract"].fillna("")
    total = len(df)

    empty = abstracts.eq("").sum() + df["abstract"].isna().sum()
    html_ent = abstracts.str.contains(r'&[a-z]+;|&#[0-9]+;', regex=True).sum()
    special_sp = abstracts.apply(lambda x: bool(SPECIAL_SPACES.search(x))).sum()
    labels = abstracts.str.contains(
        r'(BACKGROUND|OBJECTIVE|METHOD|RESULT|CONCLUSION|UNLABELLED)S?:', regex=True
    ).sum()

    print("=" * 55)
    print(f" PubMed 초록 데이터 진단 — 총 {total:,}건")
    print("=" * 55)
    print(f"  빈 abstract        : {empty:>5}건")
    print(f"  HTML entity        : {html_ent:>5}건  (&amp; &alpha; 등)")
    print(f"  특수 유니코드 공백  : {special_sp:>5}건  (\\xa0 \\u2009 등)")
    print(f"  섹션 라벨          : {labels:>5}건  (BACKGROUND: 등)")
    print("=" * 55)

    # HTML entity 샘플
    if html_ent > 0:
        print("\n[샘플] HTML entity:")
        rows = df[abstracts.str.contains(r'&[a-z]+;|&#[0-9]+;', regex=True)]
        for _, r in rows.head(2).iterrows():
            ents = re.findall(r'&[a-z]+;|&#[0-9]+;', str(r["abstract"]))
            print(f"  PMID {r['pmid']}: {ents[:5]}")

    # 섹션 라벨 샘플
    if labels > 0:
        print("\n[샘플] 섹션 라벨:")
        rows = df[abstracts.str.contains(r'(BACKGROUND|METHOD|RESULT|CONCLUSION)S?:', regex=True)]
        for _, r in rows.head(2).iterrows():
            found = re.findall(r'[A-Z ]+:', str(r["abstract"]))
            print(f"  PMID {r['pmid']}: {found[:5]}")

    print()


# ── 전처리 ────────────────────────────────────────────────────────

def clean_abstract(text):
    """단일 abstract 텍스트를 전처리한다."""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = html.unescape(html.unescape(text))      # 1. HTML entity 디코딩 (이중 인코딩 대응)
    text = SPECIAL_SPACES.sub(' ', text)           # 2. 특수 공백 → 일반 공백
    text = SECTION_LABELS.sub('', text)            # 3. 섹션 라벨 제거
    text = re.sub(r' {2,}', ' ', text).strip()     # 4. 연속 공백 정리

    return text


def run_clean(df):
    """전체 DataFrame에 전처리를 적용하고 저장한다."""
    df["abstract_clean"] = df["abstract"].apply(clean_abstract)

    empty_before = df["abstract"].isna().sum() + (df["abstract"].fillna("") == "").sum()
    empty_after = (df["abstract_clean"] == "").sum()

    print(f"전처리 완료: {len(df):,}건")
    print(f"빈 abstract: {empty_before} → {empty_after}건")

    # 변경 건수
    changed = df[df["abstract"].fillna("") != df["abstract_clean"]]
    print(f"변경된 행: {len(changed):,}건")

    # 전후 비교 샘플
    for _, row in changed.head(3).iterrows():
        before = str(row["abstract"])[:100]
        after = str(row["abstract_clean"])[:100]
        print(f"\n  [{row['pmid']}]")
        print(f"  before: {before}...")
        print(f"  after:  {after}...")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장 → {OUTPUT_CSV}")


# ── 메인 ──────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    df = pd.read_csv(INPUT_CSV)

    if mode in ("diagnose", "all"):
        diagnose(df)

    if mode in ("clean", "all"):
        run_clean(df)


if __name__ == "__main__":
    main()
