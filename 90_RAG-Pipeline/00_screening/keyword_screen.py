"""
1단계: 키워드 스크리닝

PubMed 검색 쿼리(collect_pubmed.py v3)에서 추출한 키워드로
Abstract에 관련 용어가 포함된 논문만 필터링한다.

입력: 00_preprocess/results_final.csv
출력: data/screened.csv
"""

import os
import re
import pandas as pd

# ── 경로 설정 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
INPUT_CSV = os.path.join(PROJECT_ROOT, "00_preprocess", "results_final.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "screened.csv")

# ── 키워드 리스트 (collect_pubmed.py v3 QUERY에서 추출) ──
# PubMed 검색식의 [tiab]/[MeSH] 태그를 제거하고 순수 키워드만 정리

PART_KEYWORDS = [
    "fish bone", "fish scale", "fish skin",
    "viscera", "offal",
    "fish head", "fish fin", "fish tail",
    "fish roe", "fish egg",
    "shell waste", "shrimp shell", "crab shell", "exoskeleton",
    "adductor muscle",
    "processing waste", "processing residue",
    "extract residue",
    "holdfast", "thallus",
    "kelp blade", "algal blade", "seaweed blade",
    "kelp stipe", "algal stipe", "seaweed stipe",
    "byproduct", "by-product",
    "fish maw", "swim bladder",
    "fish meal", "fishmeal", "fish silage",
    "fish gelatin", "fish cartilage",
    "fish liver", "fish gut", "fish intestin",
    "cephalothorax", "hepatopancreas",
    "shrimp head", "fish trimmings", "fish frame",
    "chitin", "chitosan",
]

CATEGORY_KEYWORDS = [
    "fish", "fishery",
    "crustacean", "shrimp", "crab", "krill", "lobster", "crayfish",
    "mollusk", "mollusc", "squid", "abalone", "oyster",
    "mussel", "scallop", "clam", "octopus", "cuttlefish",
    "seaweed", "macroalga",
    "brown algae", "phaeophyceae", "kelp", "sargassum",
    "undaria", "laminaria", "fucus", "ecklonia",
    "red algae", "rhodophyta", "gracilaria", "porphyra", "gelidium",
    "green algae", "chlorophyta", "ulva",
    "sea cucumber", "sea urchin", "jellyfish", "starfish",
    "tunicate", "sea squirt",
]

FN_KEYWORDS = [
    "anti-inflammatory", "immunomodulat",
    "antithrombotic", "anticoagulant", "fibrinolytic",
    "antihypertensive", "ace inhibit", "angiotensin converting enzyme",
    "hypocholesterolemic", "cholesterol lower",
    "blood circulation", "vasodilat",
    "hypoglycemic", "anti-diabetic", "alpha-glucosidase", "dpp-iv",
    "lipid metabolism", "hypolipidemic",
    "anti-obesity",
    "osteoblast", "bone health", "osteoporosis",
    "chondroprotect", "cartilage",
    "skin health", "collagen", "tyrosinase",
    "antioxidant", "radical scaveng", "dpph", "abts", "frap",
    "anti-aging", "anti-ageing", "elastase",
    "photoprotect", "uv protect",
    "gut health", "prebiotic",
    "digestibility",
    "hepatoprotect",
    "detoxif",
    "neuroprotect", "cognitive function", "cognitive enhancement",
    "memory improv",
    "eye health", "retinal protect",
    "anti-fatigue",
    "calcium absorption",
    "wound healing",
    "antimicrobial", "antibacterial", "antifungal", "antiviral",
    "anticancer", "antitumor", "antiproliferative", "cytotoxic",
    "cardioprotect", "renoprotect",
]


def _build_pattern(keywords: list[str]) -> re.Pattern:
    """키워드 리스트를 하나의 정규식 패턴으로 컴파일한다.
    각 키워드는 단어 경계 없이 부분 매칭 (접미사 변형 포함)."""
    escaped = [re.escape(kw) for kw in keywords]
    return re.compile("|".join(escaped), re.IGNORECASE)


def find_matches(text: str, pattern: re.Pattern) -> list[str]:
    """텍스트에서 패턴에 매칭되는 고유 키워드 목록을 반환."""
    if not isinstance(text, str) or not text.strip():
        return []
    return sorted(set(m.group().lower() for m in pattern.finditer(text)))


def screen(df: pd.DataFrame) -> pd.DataFrame:
    """3개 그룹(PART, CATEGORY, FN) 모두에서 1개 이상 매칭되는 논문만 통과."""
    pat_part = _build_pattern(PART_KEYWORDS)
    pat_cat = _build_pattern(CATEGORY_KEYWORDS)
    pat_fn = _build_pattern(FN_KEYWORDS)

    # abstract + title 합쳐서 검색
    combined = (df["title"].fillna("") + " " + df["abstract"].fillna(""))

    df = df.copy()
    df["kw_part"] = combined.apply(lambda t: find_matches(t, pat_part))
    df["kw_category"] = combined.apply(lambda t: find_matches(t, pat_cat))
    df["kw_fn"] = combined.apply(lambda t: find_matches(t, pat_fn))

    # 3그룹 모두 1개 이상 매칭
    mask = (
        df["kw_part"].apply(len).gt(0)
        & df["kw_category"].apply(len).gt(0)
        & df["kw_fn"].apply(len).gt(0)
    )

    passed = df[mask].copy()
    # 리스트를 문자열로 변환 (CSV 저장용)
    for col in ["kw_part", "kw_category", "kw_fn"]:
        passed[col] = passed[col].apply(lambda x: "; ".join(x))

    return passed


def main():
    print("=" * 60)
    print("1단계: 키워드 스크리닝")
    print("=" * 60)

    # 입력 로드
    print(f"\n입력: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"  전체 논문 수: {len(df):,}")

    # 스크리닝
    passed = screen(df)
    print(f"  통과 논문 수: {len(passed):,} ({len(passed)/len(df)*100:.1f}%)")

    # 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    passed.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUTPUT_CSV}")

    # 요약 통계
    print(f"\n── 통과율 요약 ──")
    print(f"  PART 매칭:     {(df['title'].fillna('') + ' ' + df['abstract'].fillna('')).apply(lambda t: bool(re.search(_build_pattern(PART_KEYWORDS), t))).sum():,}")
    print(f"  CATEGORY 매칭: {(df['title'].fillna('') + ' ' + df['abstract'].fillna('')).apply(lambda t: bool(re.search(_build_pattern(CATEGORY_KEYWORDS), t))).sum():,}")
    print(f"  FN 매칭:       {(df['title'].fillna('') + ' ' + df['abstract'].fillna('')).apply(lambda t: bool(re.search(_build_pattern(FN_KEYWORDS), t))).sum():,}")
    print(f"  3그룹 모두:    {len(passed):,}")


if __name__ == "__main__":
    main()
