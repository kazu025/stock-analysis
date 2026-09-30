"""large_scale_screen_result.csvから「うねり取り」候補を抽出する。

判定はscreening_core.pyの測定結果を使い、売買推奨ではなく候補の整理を行う。
"""
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR / "large_scale_screen_result.csv"
OUTPUT_FILE = SCRIPT_DIR / "swing_trade_candidates.csv"

# 初期条件。必要に応じてここだけ変更する。
MIN_RANGE_PCT = 10.0    # 値幅が10%以上あり
MIN_SWITCH_COUNT = 4    # 4回以上うねる銘柄を抽出
MAX_DAYS_SINCE_LAST_SWITCH = 20
POSITION_LOW = 30.0
POSITION_HIGH = 70.0


def main():
    df = pd.read_csv(INPUT_FILE, dtype={"Code": str})
    required = {"Code", "Ticker", "Name", "Group", "RangePct", "SwitchCount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSVに必要な列がありません: {sorted(missing)}")

    # enriched CSVがあれば、直近性と現在位置も候補条件に加える。
    enriched = SCRIPT_DIR / "large_scale_screen_result_enriched.csv"
    if enriched.exists():
        extra = pd.read_csv(enriched, dtype={"Code": str})
        extra_cols = [c for c in ["LastSwitchDate", "CurrentPrice",
                                  "CurrentPositionPct", "DaysSinceLastSwitch"]
                      if c in extra.columns]
        if extra_cols:
            df = df.drop(columns=[c for c in extra_cols if c in df.columns], errors="ignore")
            df = df.merge(extra[["Code"] + extra_cols], on="Code", how="left")

    for col in ["RangePct", "SwitchCount", "DaysSinceLastSwitch", "CurrentPositionPct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    base = (df["RangePct"] >= MIN_RANGE_PCT) & (df["SwitchCount"] >= MIN_SWITCH_COUNT)
    has_recent = "DaysSinceLastSwitch" in df.columns
    has_position = "CurrentPositionPct" in df.columns
    if has_recent:
        base &= df["DaysSinceLastSwitch"].notna() & (
            df["DaysSinceLastSwitch"] <= MAX_DAYS_SINCE_LAST_SWITCH
        )
    if has_position:
        base &= df["CurrentPositionPct"].between(POSITION_LOW, POSITION_HIGH)

    candidates = df.loc[base].copy()
    candidates["ScreeningStatus"] = "PASS"
    candidates["PriorityScore"] = (
        candidates["SwitchCount"] * 10
        + candidates["RangePct"].clip(upper=50) / 10
    )
    candidates = candidates.sort_values(
        ["PriorityScore", "SwitchCount", "RangePct"],
        ascending=False,
    )
    candidates.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"対象銘柄数: {len(df)}")
    print(f"候補銘柄数: {len(candidates)}")
    print(f"保存先: {OUTPUT_FILE}")
    if not has_recent or not has_position:
        print("注意: enriched CSVがないため、直近性・現在位置は未適用です。")
    print(candidates[["Ticker", "Name", "RangePct", "SwitchCount"]].to_string(index=False))


if __name__ == "__main__":
    main()
