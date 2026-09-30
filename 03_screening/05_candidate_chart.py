"""
スクリーニングした銘柄について、直近60営業日の値動きをチャートで確認する。

目的:
1. 終値とMA25・MA75を表示する
2. 直近60営業日の高値・安値を表示する
3. 上側20%・下側20%のゾーン境界を表示する
4. High / Lowを使って上下ゾーンへのタッチを検出する
5. 同じ側への連続タッチをまとめる
6. 交互タッチ位置をチャート上に表示する
7. スクリーニング結果と実際のチャート形状を比較する
"""

import yfinance as yf
import matplotlib.pyplot as plt


# --------------------------------------------------
# 1. 表示する銘柄
# --------------------------------------------------

TARGET_TICKER = "7751.T"
#TARGET_TICKER = "5108.T"
#TARGET_TICKER = "8801.T"
#TARGET_TICKER = "2503.T"
#TARGET_TICKER = "9020.T"

stocks = {
    "4507.T": "塩野義製薬",
    "7751.T": "キヤノン",
    "5108.T": "ブリヂストン",
    "6326.T": "クボタ",
    "4452.T": "花王",
    "8801.T": "三井不動産",
    "8802.T": "三菱地所",
    "9020.T": "JR東日本",
    "9022.T": "JR東海",
    "2503.T": "キリンHD",
}


# --------------------------------------------------
# 2. 分析条件
# --------------------------------------------------

RANGE_DAYS = 60
#ZONE_RATIO = 0.20
ZONE_RATIO = 0.25

MA25_DAYS = 25
MA75_DAYS = 75
COMPARE_DAYS = 20


# --------------------------------------------------
# 3. 銘柄名を取得する
# --------------------------------------------------

name = stocks.get(
    TARGET_TICKER,
    TARGET_TICKER
)


# --------------------------------------------------
# 4. 株価データを取得する
# --------------------------------------------------

stock = yf.Ticker(TARGET_TICKER)

df = stock.history(
    period="2y",
    auto_adjust=False
)

required_days = MA75_DAYS + COMPARE_DAYS

if len(df) < required_days:
    raise RuntimeError(
        f"データ不足: {len(df)}件"
    )


# --------------------------------------------------
# 5. 移動平均を計算する
# --------------------------------------------------

df["MA25"] = (
    df["Close"]
    .rolling(MA25_DAYS)
    .mean()
)

df["MA75"] = (
    df["Close"]
    .rolling(MA75_DAYS)
    .mean()
)


# --------------------------------------------------
# 6. MA変化率を計算する
# --------------------------------------------------

ma25_current = df["MA25"].iloc[-1]
ma25_previous = df["MA25"].iloc[-1 - COMPARE_DAYS]

ma75_current = df["MA75"].iloc[-1]
ma75_previous = df["MA75"].iloc[-1 - COMPARE_DAYS]

ma25_change_pct = (
    (ma25_current - ma25_previous)
    / ma25_previous
    * 100
)

ma75_change_pct = (
    (ma75_current - ma75_previous)
    / ma75_previous
    * 100
)


# --------------------------------------------------
# 7. 直近60営業日を取り出す
# --------------------------------------------------

df_range = df.tail(
    RANGE_DAYS
).copy()


# --------------------------------------------------
# 8. レンジを計算する
# --------------------------------------------------

range_high = df_range["High"].max()
range_low = df_range["Low"].min()

price_range = (
    range_high - range_low
)

range_pct = (
    price_range
    / range_low
    * 100
)


# --------------------------------------------------
# 9. 上側・下側ゾーン境界を計算する
# --------------------------------------------------

upper_zone = (
    range_high
    - price_range * ZONE_RATIO
)

lower_zone = (
    range_low
    + price_range * ZONE_RATIO
)


# --------------------------------------------------
# 10. High / Lowでゾーン到達を判定する
# --------------------------------------------------

df_range["UpperZone"] = (
    df_range["High"]
    >= upper_zone
)

df_range["LowerZone"] = (
    df_range["Low"]
    <= lower_zone
)


# --------------------------------------------------
# 11. ゾーンへの進入を検出する
# --------------------------------------------------

df_range["UpperTouch"] = (
    df_range["UpperZone"]
    & ~df_range["UpperZone"].shift(
        1,
        fill_value=False
    )
)

df_range["LowerTouch"] = (
    df_range["LowerZone"]
    & ~df_range["LowerZone"].shift(
        1,
        fill_value=False
    )
)


# --------------------------------------------------
# 12. タッチを時系列順に取り出す
# --------------------------------------------------

touches = []

for date, row in df_range.iterrows():

    if row["UpperTouch"]:
        touches.append(
            (date, "UPPER")
        )

    if row["LowerTouch"]:
        touches.append(
            (date, "LOWER")
        )


# --------------------------------------------------
# 13. 同じ側への連続タッチをまとめる
# --------------------------------------------------

alternating_touches = []

for date, side in touches:

    if len(alternating_touches) == 0:
        alternating_touches.append(
            (date, side)
        )
        continue

    previous_side = (
        alternating_touches[-1][1]
    )

    if side != previous_side:
        alternating_touches.append(
            (date, side)
        )


# --------------------------------------------------
# 14. 上下切り替わり数
# --------------------------------------------------

switch_count = max(
    0,
    len(alternating_touches) - 1
)


# --------------------------------------------------
# 15. 数値をコンソールに表示する
# --------------------------------------------------

print()
print(
    f"=== {name} ({TARGET_TICKER}) ==="
)
print()

print(
    f"Range Low   : {range_low:8.1f}"
)

print(
    f"Range High  : {range_high:8.1f}"
)

print(
    f"Range       : {range_pct:8.1f}%"
)

print(
    f"Lower Zone  : {lower_zone:8.1f}"
)

print(
    f"Upper Zone  : {upper_zone:8.1f}"
)

print(
    f"Switch      : {switch_count:8d}"
)

print(
    f"MA25 Change : {ma25_change_pct:+8.2f}%"
)

print(
    f"MA75 Change : {ma75_change_pct:+8.2f}%"
)


# --------------------------------------------------
# 16. 交互タッチを表示する
# --------------------------------------------------

print()
print("=== Alternating Touch ===")
print()

for date, side in alternating_touches:

    print(
        f"{date:%Y-%m-%d} "
        f"{side}"
    )


# --------------------------------------------------
# 17. チャートを作成する
# --------------------------------------------------

plt.figure(
    figsize=(14, 8)
)


# 終値
plt.plot(
    df_range.index,
    df_range["Close"],
    label="Close",
    linewidth=2
)


# MA25
plt.plot(
    df_range.index,
    df_range["MA25"],
    label="MA25",
    linewidth=1.5
)


# MA75
plt.plot(
    df_range.index,
    df_range["MA75"],
    label="MA75",
    linewidth=1.5
)


# --------------------------------------------------
# 18. レンジ高値・安値
# --------------------------------------------------

plt.axhline(
    range_high,
    linestyle="--",
    linewidth=1,
    label="Range High"
)

plt.axhline(
    range_low,
    linestyle="--",
    linewidth=1,
    label="Range Low"
)


# --------------------------------------------------
# 19. 上側・下側ゾーン境界
# --------------------------------------------------

plt.axhline(
    upper_zone,
    linestyle=":",
    linewidth=1.5,
    label="Upper Zone"
)

plt.axhline(
    lower_zone,
    linestyle=":",
    linewidth=1.5,
    label="Lower Zone"
)


# --------------------------------------------------
# 20. 交互タッチ位置を描画する
# --------------------------------------------------

for date, side in alternating_touches:

    row = df_range.loc[date]

    if side == "UPPER":

        price = row["High"]

        plt.scatter(
            date,
            price,
            marker="v",
            s=100,
            zorder=5
        )

        plt.annotate(
            "UPPER",
            (date, price),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center"
        )

    else:

        price = row["Low"]

        plt.scatter(
            date,
            price,
            marker="^",
            s=100,
            zorder=5
        )

        plt.annotate(
            "LOWER",
            (date, price),
            xytext=(0, -20),
            textcoords="offset points",
            ha="center"
        )


# --------------------------------------------------
# 21. タイトル・軸・凡例
# --------------------------------------------------

plt.title(
    f"{name} ({TARGET_TICKER})\n"
    f"Range={range_pct:.1f}%  "
    f"Switch={switch_count}  "
    f"MA25={ma25_change_pct:+.2f}%  "
    f"MA75={ma75_change_pct:+.2f}%"
)

plt.xlabel("Date")
plt.ylabel("Price")

plt.grid(
    True,
    alpha=0.3
)

plt.legend()

plt.tight_layout()

plt.show()