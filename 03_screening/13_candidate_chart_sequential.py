"""swing_trade_candidates.csvの銘柄を1銘柄ずつチャート表示する。

ウィンドウを閉じると次の銘柄を表示する。
"""
from pathlib import Path
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.family"] = "Meiryo"
rcParams["axes.unicode_minus"] = False
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_FILE = SCRIPT_DIR / "swing_trade_candidates.csv"
RANGE_DAYS = 60
ZONE_RATIO = 0.25
MA25_DAYS = 25
MA75_DAYS = 75


def make_chart(ticker, name, group=""):
    df = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
    if len(df) < RANGE_DAYS:
        print(f"{ticker}: データ不足のためスキップ")
        return
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
    ax.set_title(f"{name} ({ticker}) [{group}]\n"
                 f"Range={range_pct:.1f}%  Switch={switches}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    print(f"{name} ({ticker})  Range={range_pct:.1f}%  Switch={switches}")
    plt.show(block=True)  # ウィンドウを閉じるまで停止し、閉じたら次へ進む
    plt.close(fig)


def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"CSVがありません: {CSV_FILE}")
    candidates = pd.read_csv(CSV_FILE, dtype={"Code": str, "Ticker": str})
    for col in ["Ticker", "Name"]:
        if col not in candidates.columns:
            raise ValueError(f"CSVに必要な列がありません: {col}")
    for _, row in candidates.iterrows():
        make_chart(str(row["Ticker"]), str(row["Name"]), str(row.get("Group", "")))
    print("全銘柄のチャート表示が完了しました。")


if __name__ == "__main__":
    main()
