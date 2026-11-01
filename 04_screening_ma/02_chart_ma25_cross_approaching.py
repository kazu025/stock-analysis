"""MA25がMA75に接近している銘柄のチャートを順番に表示する。

入力:
    ma25_cross_approaching.csv

操作:
    次へボタン / N / 右矢印 / Enter : 次の銘柄
    保存ボタン / S                  : 現在のチャートを保存
    終了ボタン / Q / Esc            : 終了
"""
from pathlib import Path
from datetime import datetime
import argparse
import re

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.widgets import Button


rcParams["font.family"] = "Meiryo"
rcParams["axes.unicode_minus"] = False

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "ma25_cross_approaching.csv"
DEFAULT_CHART_DIR = SCRIPT_DIR / "charts"
MA25_DAYS = 25
MA75_DAYS = 75


def make_chart(ticker, name, group, *, number, total, period_days,
               chart_dir, auto_save):
    # MA75と表示期間を確保するため、表示日数より余裕を持って取得する。
    fetch_years = max(2, (period_days + MA75_DAYS + 30) // 250 + 1)
    df = yf.Ticker(ticker).history(
        period=f"{fetch_years}y",
        interval="1d",
        auto_adjust=False,
    )
    df = df.dropna(subset=["Close"]).sort_index()
    if len(df) < MA75_DAYS:
        print(f"{ticker}: データ不足のためスキップ ({len(df)}件)")
        return "skip"

    df["MA25"] = df["Close"].rolling(MA25_DAYS).mean()
    df["MA75"] = df["Close"].rolling(MA75_DAYS).mean()
    part = df.tail(period_days).copy()
    if part.empty:
        print(f"{ticker}: 表示データがありません")
        return "skip"

    ma25 = float(df["MA25"].iloc[-1])
    ma75 = float(df["MA75"].iloc[-1])
    gap_pct = (ma75 - ma25) / ma75 * 100 if ma75 else float("nan")

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(part.index, part["Close"], label="Close", linewidth=1.8)
    ax.plot(part.index, part["MA25"], label="MA25", linewidth=1.3)
    ax.plot(part.index, part["MA75"], label="MA75", linewidth=1.3)
    ax.set_title(
        f"{number}/{total}  {name} ({ticker}) [{group}]\n"
        f"日足・過去{period_days}営業日  MA25={ma25:.2f}  "
        f"MA75={ma75:.2f}  Gap={gap_pct:.2f}%"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout(rect=(0, 0.13, 1, 1))

    state = {"action": "next"}
    status = fig.text(0.05, 0.09, "次へ: N / → / Enter    保存: S    終了: Q / Esc    ×: 次へ")

    def advance(event=None):
        state["action"] = "next"
        plt.close(fig)

    def quit_charts(event=None):
        state["action"] = "quit"
        plt.close(fig)

    def save_chart(event=None):
        try:
            chart_dir.mkdir(parents=True, exist_ok=True)
            safe_ticker = re.sub(r"[^A-Za-z0-9._-]", "_", ticker)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = chart_dir / f"{safe_ticker}_{stamp}.png"
            fig.savefig(path, dpi=150)
            status.set_text(f"保存しました: {path.name}")
            print(f"保存: {path}")
            fig.canvas.draw_idle()
        except Exception as exc:
            status.set_text(f"保存失敗: {exc}")
            print(f"保存失敗: {exc}")

    def on_key(event):
        if event.key in ("n", "right", "enter"):
            advance()
        elif event.key == "s":
            save_chart()
        elif event.key in ("q", "escape"):
            quit_charts()

    buttons = []
    for x, label, callback in (
        (0.53, "次へ", advance),
        (0.68, "保存", save_chart),
        (0.83, "終了", quit_charts),
    ):
        button = Button(fig.add_axes([x, 0.025, 0.12, 0.045]), label)
        button.on_clicked(callback)
        buttons.append(button)
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
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help="抽出結果CSV")
    parser.add_argument("--period-days", type=int, default=200,
                        help="表示する営業日数（標準: 200）")
    parser.add_argument("--auto-save", action="store_true",
                        help="表示時に自動保存")
    parser.add_argument("--encoding", default="utf-8-sig",
                        help="CSVの文字コード")
    args = parser.parse_args()

    if args.period_days < 75:
        parser.error("--period-days は75以上にしてください")
    if not args.csv.exists():
        parser.error(f"CSVがありません: {args.csv}")

    candidates = pd.read_csv(args.csv, dtype={"Ticker": str}, encoding=args.encoding)
    for column in ("Ticker", "Name"):
        if column not in candidates.columns:
            parser.error(f"CSVに必要な列がありません: {column}")
    if candidates.empty:
        print("CSVに銘柄がありません。")
        return

    total = len(candidates)
    print(f"CSV: {args.csv.resolve()}")
    print(f"対象: {total}銘柄 / 日足・過去{args.period_days}営業日")
    print(f"保存先: {DEFAULT_CHART_DIR.resolve()}")

    shown = skipped = 0
    for number, (_, row) in enumerate(candidates.iterrows(), start=1):
        ticker = "" if pd.isna(row["Ticker"]) else str(row["Ticker"]).strip()
        name = "" if pd.isna(row["Name"]) else str(row["Name"])
        group_value = row.get("Group", "")
        group = "" if pd.isna(group_value) else str(group_value)
        if not ticker:
            skipped += 1
            continue
        try:
            action = make_chart(
                ticker,
                name,
                group,
                number=number,
                total=total,
                period_days=args.period_days,
                chart_dir=DEFAULT_CHART_DIR,
                auto_save=args.auto_save,
            )
        except KeyboardInterrupt:
            print("操作により中断しました。")
            return
        except Exception as exc:
            skipped += 1
            print(f"{ticker} {name}: スキップ ({exc})")
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
