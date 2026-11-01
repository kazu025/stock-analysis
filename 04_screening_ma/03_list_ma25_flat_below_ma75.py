"""MA25がMA75より下で、MA25の傾きが0～1％の銘柄を一覧化する。

標準条件:
    MA25 < MA75
    MA25の5営業日変化率が 0～1.0%
"""
from pathlib import Path
import argparse

import pandas as pd
import yfinance as yf


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR.parent / "data" / "large_scale_screen_result.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "ma25_flat_below_ma75.csv"
MA25_DAYS = 25
MA75_DAYS = 75


def analyse(ticker: str, name: str, group: str, slope_days: int):
    df = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=False)
    df = df.dropna(subset=["Close"]).sort_index()
    if len(df) < MA75_DAYS + slope_days:
        return None
    df["MA25"] = df["Close"].rolling(MA25_DAYS).mean()
    df["MA75"] = df["Close"].rolling(MA75_DAYS).mean()
    df = df.dropna(subset=["MA25", "MA75"])
    if len(df) <= slope_days:
        return None

    ma25 = float(df["MA25"].iloc[-1])
    ma75 = float(df["MA75"].iloc[-1])
    ma25_old = float(df["MA25"].iloc[-1 - slope_days])
    slope_pct = (ma25 - ma25_old) / ma25_old * 100
    close = float(df["Close"].iloc[-1])
    return {
        "Ticker": ticker,
        "Name": name,
        "Group": group,
        "LastDate": df.index[-1].strftime("%Y-%m-%d"),
        "Close": close,
        "MA25": ma25,
        "MA75": ma75,
        "GapPct": (ma75 - ma25) / ma75 * 100,
        "MA25SlopePct": slope_pct,
        "CloseToMA25Pct": (close - ma25) / ma25 * 100,
        "BelowMA75": ma25 < ma75,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="対象銘柄CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="一覧CSV")
    parser.add_argument("--slope-days", type=int, default=5, help="傾きを測る営業日数")
    parser.add_argument("--min-slope-pct", type=float, default=0.0,
                        help="25日線の傾きの下限（標準: 0%%）")
    parser.add_argument("--max-slope-pct", type=float, default=1.0,
                        help="25日線の傾きの上限（標準: 1%%）")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSVの文字コード")
    args = parser.parse_args()
    if (args.slope_days < 1 or args.min_slope_pct < 0
            or args.max_slope_pct < args.min_slope_pct):
        parser.error("傾きの設定値が不正です")
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
            continue
        try:
            result = analyse(ticker, name, group, args.slope_days)
            if result is None:
                print(f"{number}: {ticker} データ不足または取得失敗")
                continue
            matched = (
                result["BelowMA75"]
                and args.min_slope_pct <= result["MA25SlopePct"] <= args.max_slope_pct
            )
            if matched:
                results.append(result)
                print(f"{number}: {ticker} {name}  MA25傾き={result['MA25SlopePct']:+.2f}%")
        except Exception as exc:
            print(f"{number}: {ticker} スキップ ({exc})")

    result_df = pd.DataFrame(results)
    if result_df.empty:
        print("条件に該当する銘柄はありません。")
        return
    result_df = result_df.sort_values(["GapPct", "MA25SlopePct"], ascending=[True, True])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print()
    print(f"該当数: {len(result_df)}")
    print(
        f"条件: MA25 < MA75 / MA25傾き "
        f"{args.min_slope_pct:.2f}%～{args.max_slope_pct:.2f}% / "
        f"{args.slope_days}営業日"
    )
    print(f"保存先: {args.output.resolve()}")


if __name__ == "__main__":
    main()
