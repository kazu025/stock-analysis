"""
塩野義製薬（4507）の直近60営業日の株価と、
検出した上下ゾーンへの交互タッチをチャートに表示する。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. レンジの上側20%・下側20%をゾーンとして定義する
3. High / Lowを使って上下ゾーンへのタッチを検出する
4. 同じ側への連続タッチをまとめる
5. 検出した交互タッチをチャート上に表示する
6. 数値で検出した「うねり」がチャートでも妥当か確認する
"""

import yfinance as yf
import matplotlib.pyplot as plt


TICKER = "4507.T"
SYMBOL_NAME = "Shionogi"

RANGE_DAYS = 60
ZONE_RATIO = 0.20


# --------------------------------------------------
# 1. 過去2年間の株価を取得する
# --------------------------------------------------

stock = yf.Ticker(TICKER)

df = stock.history(
    period="2y",
    auto_adjust=False
)


# --------------------------------------------------
# 2. 直近60営業日を取り出す
# --------------------------------------------------

df_range = df.tail(RANGE_DAYS).copy()


# --------------------------------------------------
# 3. レンジを計算する
# --------------------------------------------------

range_high = df_range["High"].max()
range_low = df_range["Low"].min()

price_range = range_high - range_low


# --------------------------------------------------
# 4. 上側・下側ゾーンの境界を計算する
# --------------------------------------------------

upper_zone = range_high - price_range * ZONE_RATIO
lower_zone = range_low + price_range * ZONE_RATIO


# --------------------------------------------------
# 5. High / Lowを使ってゾーンを判定する
# --------------------------------------------------

df_range["UpperZone"] = df_range["High"] >= upper_zone
df_range["LowerZone"] = df_range["Low"] <= lower_zone


# --------------------------------------------------
# 6. ゾーンへのタッチを検出する
# --------------------------------------------------

df_range["UpperTouch"] = (
    df_range["UpperZone"]
    & ~df_range["UpperZone"].shift(1, fill_value=False)
)

df_range["LowerTouch"] = (
    df_range["LowerZone"]
    & ~df_range["LowerZone"].shift(1, fill_value=False)
)


# --------------------------------------------------
# 7. タッチした日を時系列順に取り出す
# --------------------------------------------------

touches = []

for date, row in df_range.iterrows():

    if row["UpperTouch"]:
        touches.append((date, "UPPER"))

    if row["LowerTouch"]:
        touches.append((date, "LOWER"))


# --------------------------------------------------
# 8. 同じ側への連続タッチをまとめる
# --------------------------------------------------

alternating_touches = []

for date, side in touches:

    if len(alternating_touches) == 0:
        alternating_touches.append((date, side))
        continue

    previous_side = alternating_touches[-1][1]

    if side != previous_side:
        alternating_touches.append((date, side))


# --------------------------------------------------
# 9. チャートを作成する
# --------------------------------------------------

plt.figure(figsize=(12, 6))

# 終値
plt.plot(
    df_range.index,
    df_range["Close"],
    label="Close"
)

# レンジ高値・安値
plt.axhline(
    range_high,
    linestyle=":",
    label=f"Range High {range_high:.1f}"
)

plt.axhline(
    range_low,
    linestyle=":",
    label=f"Range Low {range_low:.1f}"
)

# 上側・下側ゾーン境界
plt.axhline(
    upper_zone,
    linestyle="--",
    label=f"Upper Zone {upper_zone:.1f}"
)

plt.axhline(
    lower_zone,
    linestyle="--",
    label=f"Lower Zone {lower_zone:.1f}"
)


# --------------------------------------------------
# 10. 交互タッチをチャート上に表示する
# --------------------------------------------------

for date, side in alternating_touches:

    row = df_range.loc[date]

    if side == "UPPER":

        price = row["High"]

        plt.scatter(
            date,
            price,
            marker="^",
            s=100
        )

        plt.annotate(
            "UPPER",
            (date, price),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center"
        )

    else:

        price = row["Low"]

        plt.scatter(
            date,
            price,
            marker="v",
            s=100
        )

        plt.annotate(
            "LOWER",
            (date, price),
            xytext=(0, -18),
            textcoords="offset points",
            ha="center"
        )


# --------------------------------------------------
# 11. チャート表示
# --------------------------------------------------

plt.title(
    f"{SYMBOL_NAME} ({TICKER}) - Wave Analysis"
)

plt.xlabel("Date")
plt.ylabel("Price (JPY)")

plt.grid()
plt.legend()
plt.tight_layout()

plt.show()