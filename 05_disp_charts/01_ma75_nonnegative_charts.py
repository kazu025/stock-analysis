"""75日移動平均線の傾きが0以上の銘柄を抽出し、チャートを保存する。
入力：data/large_scale_screen_result.csv
MA75の5営業日変化率が 0%以上 の銘柄を抽出
出力CSV：05_disp_charts/ma75_slope_nonnegative.csv
CSV列：code,ticker,name
チャート保存先：05_disp_charts/charts_ma75_nonnegative/
チャート期間：過去200営業日
MA25・MA75・終値を表示
-----------------------------
期間や傾き判定日数を変更する場合：
F:\009-StockAnalysis\.venv\Scripts\python.exe F:\009-StockAnalysis\05_disp_charts\01_ma75_nonnegative_charts.py --period-days 200 --slope-days 5

"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR.parent / "data" / "large_scale_screen_result.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "ma75_slope_nonnegative.csv"
DEFAULT_CHART_DIR = SCRIPT_DIR / "charts_ma75_nonnegative"


def fetch_history(ticker, fetch_years):
    try:
        df = yf.Ticker(ticker).history(
            period=f"{fetch_years}y", interval="1d", auto_adjust=False
        )
        if df.empty:
            return ticker, None, "データなし"
        df = df.dropna(subset=["Close", "Volume"]).sort_index()
        return ticker, df, ""
    except Exception as exc:
        return ticker, None, str(exc)


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9._-一-龯ぁ-んァ-ヶ]", "_", str(text))


def save_chart(row, df, slope_pct, period_days, chart_dir):
    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA75"] = df["Close"].rolling(75).mean()
    part = df.tail(period_days)
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(part.index, part["Close"], label="Close", linewidth=1.7)
    ax.plot(part.index, part["MA25"], label="MA25", linewidth=1.2)
    ax.plot(part.index, part["MA75"], label="MA75", linewidth=1.2)
    ax.set_title(
        f"{row['Name']} ({row['Ticker']}) [{row.get('Group', '')}]\n"
        f"日足・過去{period_days}営業日  MA75傾き({row['_slope_days']}日)="
        f"{slope_pct:.2f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    chart_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{row['Code']}_{safe_name(row['Name'])}.png"
    path = chart_dir / filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chart-dir", type=Path, default=DEFAULT_CHART_DIR)
    parser.add_argument("--period-days", type=int, default=200)
    parser.add_argument("--slope-days", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--encoding", default="utf-8-sig")
    args = parser.parse_args()
    if args.period_days < 75:
        parser.error("--period-days は75以上にしてください")
    if args.slope_days < 1:
        parser.error("--slope-days は1以上にしてください")
    if not args.input.exists():
        parser.error(f"入力CSVがありません: {args.input}")

    source = pd.read_csv(args.input, dtype=str, encoding=args.encoding)
    for column in ("Code", "Ticker", "Name"):
        if column not in source.columns:
            parser.error(f"CSVに必要な列がありません: {column}")
    source = source.dropna(subset=["Ticker"]).copy()
    source["Ticker"] = source["Ticker"].astype(str).str.strip()
    source["Code"] = source["Code"].astype(str).str.replace(r"\.0$", "", regex=True)
    fetch_years = max(2, (args.period_days + 75 + args.slope_days + 30) // 250 + 1)

    histories = {}
    print(f"対象: {len(source)}銘柄 / 75日線の傾き判定: {args.slope_days}営業日")
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(fetch_history, ticker, fetch_years)
                   for ticker in source["Ticker"]]
        for future in as_completed(futures):
            ticker, df, error = future.result()
            if df is not None:
                histories[ticker] = df
            elif error:
                print(f"取得失敗 {ticker}: {error}")

    selected = []
    chart_count = 0
    for _, row in source.iterrows():
        ticker = row["Ticker"]
        df = histories.get(ticker)
        if df is None or len(df) < 75 + args.slope_days:
            continue
        ma75 = df["Close"].rolling(75).mean()
        now = ma75.iloc[-1]
        old = ma75.iloc[-1 - args.slope_days]
        if pd.isna(now) or pd.isna(old):
            continue
        slope_pct = (float(now) - float(old)) / float(old) * 100 if old else 0.0
        if slope_pct < 0:
            continue
        output_row = {"code": row["Code"], "ticker": ticker, "name": row["Name"]}
        selected.append(output_row)
        chart_row = row.to_dict()
        chart_row["_slope_days"] = args.slope_days
        save_chart(chart_row, df, slope_pct, args.period_days, args.chart_dir)
        chart_count += 1

    result = pd.DataFrame(selected, columns=["code", "ticker", "name"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"抽出: {len(result)}銘柄")
    print(f"CSV: {args.output.resolve()}")
    print(f"チャート: {args.chart_dir.resolve()} ({chart_count}枚)")


if __name__ == "__main__":
    main()
