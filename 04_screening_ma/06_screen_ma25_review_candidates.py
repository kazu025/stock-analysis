"""ma25_cross_review_candidates.csvを出来高と上抜け条件で再選別する。"""
"""
株価がMA25より上
MA25が上昇
MA25とMA75の差が縮小
出来高が20日平均以上
直近20日高値を更新
株価がMA75より上
"""
from pathlib import Path
import argparse

import pandas as pd
import yfinance as yf


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "ma25_cross_review_candidates.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "ma25_review_second_screen.csv"


def ticker_code(value):
    code = str(value).strip()
    if code.endswith(".0"):
        code = code[:-2]
    return code if "." in code else f"{code}.T"


def analyse(ticker, name):
    df = yf.Ticker(ticker).history(period="2y", interval="1d", auto_adjust=False)
    if df.empty:
        return None
    df = df.dropna(subset=["Close", "Volume"]).sort_index()
    if len(df) < 100:
        return None
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA75"] = df["Close"].rolling(75).mean()
    df["Vol20"] = df["Volume"].rolling(20).mean()
    df["High20Prev"] = df["Close"].shift(1).rolling(20).max()
    row = df.iloc[-1]
    prev5 = df.iloc[-6]
    if pd.isna(row[["MA25", "MA75", "Vol20", "High20Prev"]]).any():
        return None

    close = float(row["Close"])
    ma25 = float(row["MA25"])
    ma75 = float(row["MA75"])
    ma25_slope = (ma25 - float(prev5["MA25"])) / float(prev5["MA25"]) * 100
    spread = ma25 - ma75
    spread_prev = float(prev5["MA25"]) - float(prev5["MA75"])
    volume = float(row["Volume"])
    vol20 = float(row["Vol20"])
    high20_prev = float(row["High20Prev"])

    checks = {
        "PriceAboveMA25": close > ma25,
        "MA25Rising": ma25_slope > 0,
        "SpreadShrinking": spread > spread_prev,
        "VolumeAbove20Avg": volume >= vol20,
        "High20Breakout": close >= high20_prev,
        "PriceAboveMA75": close > ma75,
    }
    score = sum(checks.values())
    if score >= 5:
        priority = "候補"
    elif score >= 3:
        priority = "監視"
    else:
        priority = "保留"
    return {
        "コード": ticker.removesuffix(".T"),
        "銘柄名": name,
        "判定": priority,
        "スコア": score,
        "終値": close,
        "MA25": ma25,
        "MA75": ma75,
        "MA25傾き5日%": ma25_slope,
        "出来高倍率": volume / vol20 if vol20 else float("nan"),
        "直近20日高値更新": checks["High20Breakout"],
        "MA25上": checks["PriceAboveMA25"],
        "MA25上昇": checks["MA25Rising"],
        "MA25_MA75差縮小": checks["SpreadShrinking"],
        "出来高20日平均以上": checks["VolumeAbove20Avg"],
        "MA75上": checks["PriceAboveMA75"],
        "基準日": df.index[-1].strftime("%Y-%m-%d"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.csv.exists():
        parser.error(f"CSVがありません: {args.csv}")
    source = pd.read_csv(args.csv, dtype=str, encoding="utf-8-sig")
    for column in ("コード", "銘柄名"):
        if column not in source.columns:
            parser.error(f"CSVに必要な列がありません: {column}")

    results = []
    for number, row in source.iterrows():
        code = ticker_code(row["コード"])
        name = str(row["銘柄名"]).strip()
        try:
            result = analyse(code, name)
            if result is None:
                print(f"{number + 1}: {code} データ取得失敗")
                continue
            results.append(result)
            print(f"{number + 1}: {code} {name} {result['判定']} ({result['スコア']}/6)")
        except Exception as exc:
            print(f"{number + 1}: {code} スキップ: {exc}")
    if not results:
        print("分析結果がありません。")
        return
    output = pd.DataFrame(results).sort_values(
        ["スコア", "出来高倍率"], ascending=[False, False]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"保存先: {args.output.resolve()}")


if __name__ == "__main__":
    main()
