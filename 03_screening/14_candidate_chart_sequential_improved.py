"""swing_trade_candidates.csvの銘柄を1銘柄ずつチャート表示する。

ウィンドウを閉じると次の銘柄を表示する。
"""
from pathlib import Path
import argparse
from datetime import datetime
import re
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.widgets import Button

rcParams["font.family"] = "Meiryo"
rcParams["axes.unicode_minus"] = False
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_FILE = SCRIPT_DIR / "swing_trade_candidates.csv"
RANGE_DAYS = 60
ZONE_RATIO = 0.25
MA25_DAYS = 25
MA75_DAYS = 75


def make_chart(ticker, name, group="", *, position=1, total=1,
               session_position=1, session_total=1, save_dir=None, auto_save=False):
    df = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
    df = df.dropna(subset=["High", "Low", "Close"]).sort_index()
    if len(df) < RANGE_DAYS:
        print(f"{ticker}: データ不足のためスキップ")
        return "skip"
    df["MA25"] = df["Close"].rolling(MA25_DAYS).mean()
    df["MA75"] = df["Close"].rolling(MA75_DAYS).mean()
    part = df.tail(RANGE_DAYS).copy()
    high, low = part["High"].max(), part["Low"].min()
    width = high - low
    upper = high - width * ZONE_RATIO
    lower = low + width * ZONE_RATIO
    up = part["High"] >= upper
    down = part["Low"] <= lower
    touches = []
    for i, date in enumerate(part.index):
        if bool(up.iloc[i]) and not (i and bool(up.iloc[i - 1])):
            touches.append((date, "UPPER"))
        if bool(down.iloc[i]) and not (i and bool(down.iloc[i - 1])):
            touches.append((date, "LOWER"))
    alternating = []
    for date, side in touches:
        if not alternating or alternating[-1][1] != side:
            alternating.append((date, side))
    switches = max(0, len(alternating) - 1)
    range_pct = width / low * 100 if low > 0 else float("nan")

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(part.index, part["Close"], label="Close", linewidth=2)
    ax.plot(part.index, part["MA25"], label="MA25", linewidth=1.3)
    ax.plot(part.index, part["MA75"], label="MA75", linewidth=1.3)
    ax.axhline(high, linestyle="--", linewidth=1, label="Range High")
    ax.axhline(low, linestyle="--", linewidth=1, label="Range Low")
    ax.axhline(upper, linestyle=":", linewidth=1.5, label="Upper Zone")
    ax.axhline(lower, linestyle=":", linewidth=1.5, label="Lower Zone")
    for date, side in alternating:
        price = part.loc[date, "High" if side == "UPPER" else "Low"]
        ax.scatter(date, price, marker="v" if side == "UPPER" else "^",
                   s=90, zorder=5)
        ax.annotate(side, (date, price), xytext=(0, 12 if side == "UPPER" else -20),
                    textcoords="offset points", ha="center")
    ax.set_title(f"CSV {position}/{total} | 今回 {session_position}/{session_total}\n"
                 f"{name} ({ticker}) [{group}]\n"
                 f"Range={range_pct:.1f}%  Switch={switches}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    print(f"{name} ({ticker})  Range={range_pct:.1f}%  Switch={switches}")
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
            folder = Path(save_dir) if save_dir else SCRIPT_DIR / "charts"
            folder.mkdir(parents=True, exist_ok=True)
            safe_ticker = re.sub(r"[^A-Za-z0-9._-]", "_", ticker)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = folder / f"{safe_ticker}_{stamp}.png"
            fig.savefig(path, dpi=150)
            status.set_text(f"保存しました: {path.name}")
            print(f"保存: {path}")
        except Exception as exc:
            status.set_text(f"保存失敗: {exc}")
            print(f"保存失敗: {exc}")
        fig.canvas.draw_idle()

    def on_key(event):
        if event.key in ("n", "right", "enter"):
            advance()
        elif event.key == "s":
            save_chart()
        elif event.key in ("q", "escape"):
            quit_charts()

    # show() が戻るまで Button の参照を保持する。
    buttons = []
    for x, label, callback in [(0.53, "次へ", advance),
                                (0.68, "保存", save_chart),
                                (0.83, "終了", quit_charts)]:
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
    parser.add_argument("--csv", type=Path, default=CSV_FILE, help="候補CSV")
    parser.add_argument("--start", type=int, default=1, help="CSVの何番目から（1始まり）")
    parser.add_argument("--limit", type=int, default=0, help="対象行数の上限（0=残り全部）")
    parser.add_argument("--list-only", action="store_true", help="指定範囲のCSV順を確認して終了")
    parser.add_argument("--save-dir", type=Path, default=SCRIPT_DIR / "charts")
    parser.add_argument("--auto-save", action="store_true", help="表示時にPNGを自動保存")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSVの文字コード（例: cp932）")
    args = parser.parse_args()
    if args.start < 1 or args.limit < 0:
        parser.error("--start は1以上、--limit は0以上にしてください")
    if not args.csv.exists():
        parser.error(f"CSVがありません: {args.csv}")
    candidates = pd.read_csv(args.csv, dtype={"Code": str, "Ticker": str},
                             encoding=args.encoding)
    for col in ["Ticker", "Name"]:
        if col not in candidates.columns:
            raise ValueError(f"CSVに必要な列がありません: {col}")
    total = len(candidates)
    if not total:
        print("CSVに候補銘柄がありません。")
        return
    if args.start > total:
        parser.error(f"開始位置が候補数 {total} を超えています")
    stop = min(total, args.start - 1 + args.limit) if args.limit else total
    selected = candidates.iloc[args.start - 1:stop]
    print(f"CSV: {args.csv.resolve()}\n全{total}行 / 対象: {args.start}～{stop}番目")
    for index, row in selected.iterrows():
        print(f"{index + 1:4d}: {row['Ticker']}  {row['Name']}  {row.get('Group', '')}")
    if args.list_only:
        return
    shown = skipped = 0
    for number, (index, row) in enumerate(selected.iterrows(), start=1):
        ticker = "" if pd.isna(row["Ticker"]) else str(row["Ticker"]).strip()
        name = "" if pd.isna(row["Name"]) else str(row["Name"])
        group = row.get("Group", "")
        group = "" if pd.isna(group) else str(group)
        try:
            if not ticker:
                raise ValueError("Tickerが空です")
            action = make_chart(ticker, name, group, position=index + 1, total=total,
                                session_position=number, session_total=len(selected),
                                save_dir=args.save_dir, auto_save=args.auto_save)
        except KeyboardInterrupt:
            print("操作により中断しました。")
            return
        except Exception as exc:
            skipped += 1
            print(f"CSV {index + 1}: {ticker} をスキップ: {exc}")
            continue
        if action == "skip":
            skipped += 1
        else:
            shown += 1
        if action == "quit":
            print(f"終了しました。次回は --start {index + 1} で現在の銘柄から再開できます。")
            break
    else:
        print("指定範囲の確認が完了しました。")
    print(f"表示: {shown}銘柄 / スキップ: {skipped}銘柄")


if __name__ == "__main__":
    main()

