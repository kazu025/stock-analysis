"""MA25がMA75を下から上抜けそうな銘柄を抽出する。

判定条件:
    - 最新のMA25がMA75より下
    - MA25の傾きがMA75より大きい
    - MA75の傾きが0以上（横ばい以上）
    - MA25とMA75の差が、比較日前より縮小

入力CSVは Ticker / Name 列を必須とし、Group 列は任意で利用する。
"""
from pathlib import Path
import argparse

import pandas as pd
import yfinance as yf


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR.parent / "data" / "large_scale_screen_result.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "ma25_cross_approaching.csv"

MA25_DAYS = 25
MA75_DAYS = 75
SLOPE_DAYS = 5
COMPARE_DAYS = 20


def analyse_stock(ticker: str, name: str, group: str) -> dict | None:
    """1銘柄を分析し、判定結果を返す。"""
    df = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
    if df.empty:
        return None

    df = df.dropna(subset=["Close"]).sort_index()
    required_days = MA75_DAYS + COMPARE_DAYS + SLOPE_DAYS
    if len(df) < required_days:
        return None

    df["MA25"] = df["Close"].rolling(MA25_DAYS).mean()
    df["MA75"] = df["Close"].rolling(MA75_DAYS).mean()
    df = df.dropna(subset=["MA25", "MA75"])
    if len(df) <= COMPARE_DAYS + SLOPE_DAYS:
        return None

    ma25_now = float(df["MA25"].iloc[-1])
    ma75_now = float(df["MA75"].iloc[-1])
    ma25_old = float(df["MA25"].iloc[-1 - COMPARE_DAYS])
    ma75_old = float(df["MA75"].iloc[-1 - COMPARE_DAYS])
    ma25_slope_base = float(df["MA25"].iloc[-1 - SLOPE_DAYS])
    ma75_slope_base = float(df["MA75"].iloc[-1 - SLOPE_DAYS])

    # 株価水準が違う銘柄同士でも比較しやすいよう、傾きは変化率で比較する。
    ma25_slope_pct = (ma25_now - ma25_slope_base) / ma25_slope_base * 100
    ma75_slope_pct = (ma75_now - ma75_slope_base) / ma75_slope_base * 100
    spread_now = ma25_now - ma75_now
    spread_old = ma25_old - ma75_old
    gap_pct = (ma75_now - ma25_now) / ma75_now * 100

    below = ma25_now < ma75_now
    slope_fast = ma25_slope_pct > ma75_slope_pct
    ma75_flat_or_up = ma75_slope_pct >= 0
    spread_shrinking = spread_now > spread_old
    approaching = below and slope_fast and ma75_flat_or_up and spread_shrinking

    return {
        "Ticker": ticker,
        "Name": name,
        "Group": group,
        "MA25": ma25_now,
        "MA75": ma75_now,
        "GapPct": gap_pct,
        "MA25SlopePct": ma25_slope_pct,
        "MA75SlopePct": ma75_slope_pct,
        "SpreadNow": spread_now,
        "Spread{0}DaysAgo".format(COMPARE_DAYS): spread_old,
        "BelowMA75": below,
        "MA25SlopeGreater": slope_fast,
        "MA75FlatOrUp": ma75_flat_or_up,
        "SpreadShrinking": spread_shrinking,
        "Approaching": approaching,
        "LastDate": df.index[-1].strftime("%Y-%m-%d"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="対象銘柄CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="結果CSV")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSVの文字コード")
    parser.add_argument("--all", action="store_true", help="該当銘柄だけでなく全銘柄を結果に出す")
    args = parser.parse_args()

    if not args.csv.exists():
        parser.error(f"CSVがありません: {args.csv}")
    candidates = pd.read_csv(args.csv, dtype={"Ticker": str}, encoding=args.encoding)
    for column in ("Ticker", "Name"):
        if column not in candidates.columns:
            parser.error(f"CSVに必要な列がありません: {column}")

    results = []
    for number, (_, row) in enumerate(candidates.iterrows(), start=1):
        ticker = "" if pd.isna(row["Ticker"]) else str(row["Ticker"]).strip()
        name = "" if pd.isna(row["Name"]) else str(row["Name"])
        group_value = row.get("Group", "")
        group = "" if pd.isna(group_value) else str(group_value)
        if not ticker:
            print(f"{number}: Tickerが空のためスキップ")
            continue
        try:
            result = analyse_stock(ticker, name, group)
            if result is None:
                print(f"{number}: {ticker} {name} データ不足または取得失敗")
                continue
            results.append(result)
            mark = "候補" if result["Approaching"] else "--"
            print(f"{number}: {ticker} {name} {mark} Gap={result['GapPct']:.2f}%")
        except Exception as exc:
            print(f"{number}: {ticker} {name} スキップ: {exc}")

    result_df = pd.DataFrame(results)
    if result_df.empty:
        print("分析結果がありません。")
        return
    result_df = result_df.sort_values(
        ["Approaching", "GapPct", "MA25SlopePct"],
        ascending=[False, True, False],
    )
    output_df = result_df if args.all else result_df[result_df["Approaching"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print()
    print(f"候補数: {len(output_df)} / 分析数: {len(result_df)}")
    print(f"保存先: {args.output.resolve()}")


if __name__ == "__main__":
    main()
