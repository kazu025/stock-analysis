"""ma25_cross_review_candidates.csvの銘柄を順番にチャート表示する。

チャート描画と操作は 02_chart_ma25_cross_approaching.py と共通。
"""
from pathlib import Path
import runpy
import sys
import tempfile

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_CSV = SCRIPT_DIR / "ma25_cross_review_candidates.csv"
CHART_SCRIPT = SCRIPT_DIR / "02_chart_ma25_cross_approaching.py"


def normalize_ticker(value):
    code = str(value).strip()
    if code.endswith(".0"):
        code = code[:-2]
    if code and "." not in code:
        code = f"{code}.T"
    return code


def main():
    source = SOURCE_CSV
    forwarded = sys.argv[1:]
    if "--csv" in forwarded:
        index = forwarded.index("--csv")
        if index + 1 < len(forwarded):
            source = Path(forwarded[index + 1])
    if not source.exists():
        raise SystemExit(f"CSVがありません: {source}")

    candidates = pd.read_csv(source, dtype=str, encoding="utf-8-sig")
    required = ("コード", "銘柄名")
    if any(column not in candidates.columns for column in required):
        raise SystemExit("CSVに必要な列がありません: コード, 銘柄名")

    normalized = pd.DataFrame({
        "Ticker": candidates["コード"].map(normalize_ticker),
        "Name": candidates["銘柄名"].fillna("").astype(str).str.strip(),
        "Group": "",
    })

    with tempfile.TemporaryDirectory(prefix="ma25_review_") as temp_dir:
        normalized_csv = Path(temp_dir) / "normalized.csv"
        normalized.to_csv(normalized_csv, index=False, encoding="utf-8-sig")
        sys.argv = [str(CHART_SCRIPT), "--csv", str(normalized_csv),
                    "--encoding", "utf-8-sig", *forwarded]
        # --csvは上で正規化した一時ファイルを優先する。
        for index, arg in enumerate(sys.argv):
            if arg == "--csv" and index + 1 < len(sys.argv) and index > 0:
                sys.argv[index + 1] = str(normalized_csv)
        runpy.run_path(str(CHART_SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
