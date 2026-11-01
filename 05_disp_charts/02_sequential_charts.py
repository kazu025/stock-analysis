"""code,ticker,銘柄名形式のCSVを順番にチャート表示する。
入力：data/large_scale_screen_result.csv
MA75の5営業日変化率が 0%以上 の銘柄を抽出
出力CSV：05_disp_charts/ma75_slope_nonnegative.csv
CSV列：code,ticker,name
チャート保存先：05_disp_charts/charts_ma75_nonnegative/
チャート期間：過去200営業日
MA25・MA75・終値を表示
-----------------------------
[銘柄保存] ボタンを [次へ] の左側に追加
表示中の銘柄をCSVへ保存
同じ銘柄を再保存した場合は重複せず更新
保存形式：code,ticker,銘柄名
python.exe .\05_disp_charts\02_sequential_charts.py 
  --csv .\05_disp_charts\ma75_slope_nonnegative.csv 
  --selected-csv .\05_disp_charts\my_selected_stocks.csv
"""
from datetime import datetime
from pathlib import Path
import argparse
import re

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.widgets import Button
import pandas as pd
import yfinance as yf


rcParams["font.family"] = "Meiryo"
rcParams["axes.unicode_minus"] = False

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "ma75_slope_nonnegative.csv"
DEFAULT_CHART_DIR = SCRIPT_DIR / "charts_sequential"
DEFAULT_SELECTED_CSV = SCRIPT_DIR / "selected_stocks.csv"


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9._-一-龯ぁ-んァ-ヶ]", "_", str(text))


def save_stock(row, selected_csv):
    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    columns = ["code", "ticker", "銘柄名"]
    new_row = pd.DataFrame([{
        "code": str(row["code"]).strip(),
        "ticker": str(row["ticker"]).strip(),
        "銘柄名": str(row["銘柄名"]).strip(),
    }], columns=columns)
    if selected_csv.exists():
        saved = pd.read_csv(selected_csv, dtype=str, encoding="utf-8-sig")
        if all(column in saved.columns for column in columns):
            saved = saved[columns]
            saved = saved[saved["ticker"].astype(str) != str(row["ticker"]).strip()]
            result = pd.concat([saved, new_row], ignore_index=True)
        else:
            result = new_row
    else:
        result = new_row
    result.to_csv(selected_csv, index=False, encoding="utf-8-sig")


def show_chart(row, number, total, period_days, chart_dir, selected_csv, auto_save):
    ticker = str(row["ticker"]).strip()
    code = str(row["code"]).strip()
    name = str(row["銘柄名"]).strip()
    fetch_years = max(2, (period_days + 75 + 30) // 250 + 1)
    df = yf.Ticker(ticker).history(
        period=f"{fetch_years}y", interval="1d", auto_adjust=False
    )
    df = df.dropna(subset=["Close"]).sort_index()
    if len(df) < 75:
        print(f"{ticker}: データ不足のためスキップ")
        return "skip"

    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA75"] = df["Close"].rolling(75).mean()
    part = df.tail(period_days)
    ma25 = float(df["MA25"].iloc[-1])
    ma75 = float(df["MA75"].iloc[-1])
    gap = (ma75 - ma25) / ma75 * 100 if ma75 else float("nan")

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(part.index, part["Close"], label="Close", linewidth=1.8)
    ax.plot(part.index, part["MA25"], label="MA25", linewidth=1.3)
    ax.plot(part.index, part["MA75"], label="MA75", linewidth=1.3)
    ax.set_title(
        f"{number}/{total}  {name} ({code}, {ticker})\n"
        f"日足・過去{period_days}営業日  MA25={ma25:.2f}  "
        f"MA75={ma75:.2f}  Gap={gap:.2f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout(rect=(0, 0.13, 1, 1))

    state = {"action": "next"}
    status = fig.text(0.05, 0.09, "次へ: N / → / Enter    保存: S    終了: Q / Esc")

    def next_chart(event=None):
        state["action"] = "next"
        plt.close(fig)

    def quit_viewer(event=None):
        state["action"] = "quit"
        plt.close(fig)

    def save_chart(event=None):
        chart_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = chart_dir / f"{code}_{safe_name(name)}_{stamp}.png"
        fig.savefig(path, dpi=150)
        status.set_text(f"保存しました: {path.name}")
        fig.canvas.draw_idle()
        print(f"保存: {path}")

    def save_stock_button(event=None):
        save_stock(row, selected_csv)
        status.set_text(f"銘柄を保存しました: {selected_csv.name}")
        fig.canvas.draw_idle()
        print(f"銘柄保存: {selected_csv}")

    def on_key(event):
        if event.key in ("n", "right", "enter"):
            next_chart()
        elif event.key == "s":
            save_chart()
        elif event.key in ("q", "escape"):
            quit_viewer()

    for x, label, callback in (
        (0.38, "銘柄保存", save_stock_button),
        (0.53, "次へ", next_chart),
        (0.68, "保存", save_chart),
        (0.83, "終了", quit_viewer),
    ):
        button = Button(fig.add_axes([x, 0.025, 0.12, 0.045]), label)
        button.on_clicked(callback)
    fig.canvas.mpl_connect("key_press_event", on_key)

    try:
        if auto_save:
            save_chart()
        plt.show(block=True)
    finally:
        plt.close(fig)
    return state["action"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--period-days", type=int, default=200)
    parser.add_argument("--chart-dir", type=Path, default=DEFAULT_CHART_DIR)
    parser.add_argument("--selected-csv", type=Path, default=DEFAULT_SELECTED_CSV,
                        help="銘柄保存ボタンの保存先CSV")
    parser.add_argument("--auto-save", action="store_true")
    parser.add_argument("--encoding", default="utf-8-sig")
    args = parser.parse_args()
    if args.period_days < 75:
        parser.error("--period-days は75以上にしてください")
    if not args.csv.exists():
        parser.error(f"CSVがありません: {args.csv}")

    source = pd.read_csv(args.csv, dtype=str, encoding=args.encoding)
    for column in ("code", "ticker"):
        if column not in source.columns:
            parser.error(f"CSVに必要な列がありません: {column}")
    # 入力作成元によって名称列が name または 銘柄名になるため、両方に対応する。
    if "銘柄名" not in source.columns:
        if "name" in source.columns:
            source = source.rename(columns={"name": "銘柄名"})
        else:
            parser.error("CSVに必要な列がありません: 銘柄名 または name")
    if source.empty:
        print("CSVに銘柄がありません。")
        return

    total = len(source)
    print(f"対象: {total}銘柄 / 日足・過去{args.period_days}営業日")
    shown = skipped = 0
    for number, (_, row) in enumerate(source.iterrows(), start=1):
        try:
            action = show_chart(
                row, number, total, args.period_days, args.chart_dir,
                args.selected_csv, args.auto_save
            )
        except KeyboardInterrupt:
            print("操作により中断しました。")
            return
        except Exception as exc:
            skipped += 1
            print(f"{row['ticker']} {row['銘柄名']}: スキップ ({exc})")
            continue
        if action == "skip":
            skipped += 1
        else:
            shown += 1
        if action == "quit":
            print("終了しました。")
            break
    else:
        print("指定銘柄の表示が完了しました。")
    print(f"表示: {shown}銘柄 / スキップ: {skipped}銘柄")


if __name__ == "__main__":
    main()
