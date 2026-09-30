"""
塩野義製薬（4507）の直近60営業日の株価について、
上側・下側ゾーンへの到達回数を調べる。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. レンジの上側20%・下側20%をゾーンとして定義する
3. 終値がゾーン内にあるか判定する
4. 「ゾーン外 → ゾーン内」への変化を検出する
5. 連続してゾーン内にいる場合は1回の到達として数える

これにより、単なる「ゾーン内営業日数」ではなく、
価格が何回ゾーンへ到達したかを調べる。
"""

import yfinance as yf


TICKER = "4507.T"
SYMBOL_NAME = "塩野義製薬"

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
# 3. 60営業日の高値・安値・値幅を求める
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
# 5. 終値がゾーン内にあるか判定する
# --------------------------------------------------

df_range["UpperZone"] = df_range["Close"] >= upper_zone
df_range["LowerZone"] = df_range["Close"] <= lower_zone


# --------------------------------------------------
# 6. ゾーンへの到達を検出する
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
# 7. 到達回数を数える
# --------------------------------------------------

upper_touch_count = df_range["UpperTouch"].sum()
lower_touch_count = df_range["LowerTouch"].sum()


# --------------------------------------------------
# 8. 結果を表示する
# --------------------------------------------------

print("=== レンジ・タッチ回数分析 ===")
print(f"銘柄       : {SYMBOL_NAME} ({TICKER})")
print(f"分析期間   : {RANGE_DAYS} 営業日")
print()

print("=== レンジ ===")
print(f"安値       : {range_low:8.1f} 円")
print(f"高値       : {range_high:8.1f} 円")
print(f"値幅       : {price_range:8.1f} 円")

print()

print("=== ゾーン ===")
print(f"上側境界   : {upper_zone:8.1f} 円")
print(f"下側境界   : {lower_zone:8.1f} 円")

print()

print("=== タッチ回数 ===")
print(f"上側タッチ : {upper_touch_count:4d} 回")
print(f"下側タッチ : {lower_touch_count:4d} 回")

print()

print("=== タッチした日 ===")

for date, row in df_range.iterrows():

    if row["UpperTouch"]:
        print(
            f"{date.strftime('%Y-%m-%d')} "
            f"上側  Close={row['Close']:8.1f}"
        )

    if row["LowerTouch"]:
        print(
            f"{date.strftime('%Y-%m-%d')} "
            f"下側  Close={row['Close']:8.1f}"
        )