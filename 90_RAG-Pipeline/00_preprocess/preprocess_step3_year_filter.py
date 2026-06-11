"""
Step 3: 2000년 이전 논문 제거

- 근거: 2000년 이전 데이터는 전체의 3.8%(256건)로 미미하며,
        수산부산물 기능성 연구가 본격화된 시점이 2000년대 이후임.
        (연도별 분포 → docs/preprocessing.md 참고)
- 입력: results_cleaned_nonan.csv
- 출력: results_final.csv
"""

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "results_cleaned_nonan.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "results_final.csv")
YEAR_CUTOFF = 2000


def main():
    df = pd.read_csv(INPUT_CSV)
    before = len(df)

    df = df[df["year"] >= YEAR_CUTOFF]

    after = len(df)
    dropped = before - after

    print(f"총 {before:,}건 → {after:,}건 (제거: {dropped}건, {YEAR_CUTOFF}년 이전)")
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"저장 → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
