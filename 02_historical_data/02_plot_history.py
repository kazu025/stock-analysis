"""
塩野義製薬（4507）の直近250営業日の終値と25日移動平均を表示する。

目的:
1. 250営業日の株価推移を確認する
2. 25日,75日移動平均によって株価の大きな流れを確認する
3. 上昇・下降・横ばいの違いを目で確認する
"""

import yfinance as yf
import matplotlib.pyplot as plt


TICKER = "4507.T"
SYMBOL_NAME = "Shionogi"
DAYS = 250


# --------------------------------------------------
# 1. 過去2年間の株価を取得する
# --------------------------------------------------

stock = yf.Ticker(TICKER)

df = stock.history(
    period="2y",
    auto_adjust=False
)


# --------------------------------------------------
# 2. 直近250営業日を取り出す
# --------------------------------------------------

df250 = df.tail(DAYS)

# --------------------------------------------------
# 3. 移動平均を計算する
# --------------------------------------------------
MA25_DAYS = 25
MA75_DAYS = 75

df250 = df250.copy()

df250["MA25"] = (
    df250["Close"]
    .rolling(MA25_DAYS)
    .mean()
)

df250["MA75"] = (
    df250["Close"]
    .rolling(MA75_DAYS)
    .mean()
)

# --------------------------------------------------
# 4. 250日高値・安値を求める
# --------------------------------------------------

high_250 = df250["High"].max()
low_250 = df250["Low"].min()


# --------------------------------------------------
# 5. 終値をグラフにする
# --------------------------------------------------

plt.figure(figsize=(12, 6))

plt.plot(
    df250.index,
    df250["Close"],
    label="Close"
)

# 25日移動平均
plt.plot(
    df250.index,
    df250["MA25"],
    label="MA25"
)
# 75日移動平均
plt.plot(
    df250.index,
    df250["MA75"],
    label="MA75"
)

plt.axhline(
    high_250,
    linestyle="--",
    label=f"250-day High {high_250:.1f}"
)

plt.axhline(
    low_250,
    linestyle="--",
    label=f"250-day Low {low_250:.1f}"
)

plt.title(f"{SYMBOL_NAME} ({TICKER}) - 250 Trading Days")
plt.xlabel("Date")
plt.ylabel("Price (JPY)")

plt.grid()
plt.legend()
plt.tight_layout()

plt.show()