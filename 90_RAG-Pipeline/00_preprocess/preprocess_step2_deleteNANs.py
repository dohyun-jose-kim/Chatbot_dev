"""
Step 2: abstract 결측치(빈 문자열) 행 제거

- 입력: results_cleaned.csv (preprocess_step1.py 출력)
- 출력: results_cleaned_nonan.csv
- abstract_clean 컬럼이 비어있는 행을 제거
"""

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "results_cleaned.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "results_cleaned_nonan.csv")


def main():
    df = pd.read_csv(INPUT_CSV)
    before = len(df)

    # abstract_clean이 비어있거나 NaN인 행 제거
    df = df[df["abstract_clean"].fillna("").str.strip().ne("")]

    after = len(df)
    dropped = before - after

    print(f"총 {before:,}건 → {after:,}건 (제거: {dropped}건)")
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"저장 → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
