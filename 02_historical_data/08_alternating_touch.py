"""
塩野義製薬（4507）の直近60営業日について、
上側・下側ゾーンへの交互タッチを調べる。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. レンジの上側20%・下側20%をゾーンとして定義する
3. High / Lowを使ってゾーンへのタッチを検出する
4. 同じ側への連続したタッチをまとめる
5. 上側・下側を交互に移動した回数を調べる

例:
    下 → 上 → 下 → 下 → 下 → 上 → 下

これを、

    下 → 上 → 下 → 上 → 下

として扱う。
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

    # 最初のタッチはそのまま追加する
    if len(alternating_touches) == 0:
        alternating_touches.append((date, side))
        continue

    # 前回とは違う側の場合だけ追加する
    previous_side = alternating_touches[-1][1]

    if side != previous_side:
        alternating_touches.append((date, side))


# --------------------------------------------------
# 9. 上下の切り替わり回数を計算する
# --------------------------------------------------

switch_count = max(0, len(alternating_touches) - 1)


# --------------------------------------------------
# 10. 結果を表示する
# --------------------------------------------------

print("=== 交互タッチ分析 ===")
print(f"銘柄       : {SYMBOL_NAME} ({TICKER})")
print(f"分析期間   : {RANGE_DAYS} 営業日")
print()

print("=== レンジ ===")
print(f"安値       : {range_low:8.1f} 円")
print(f"高値       : {range_high:8.1f} 円")
print()

print("=== ゾーン ===")
print(f"上側境界   : {upper_zone:8.1f} 円")
print(f"下側境界   : {lower_zone:8.1f} 円")
print()

print("=== 全タッチ ===")

for date, side in touches:
    print(
        f"{date.strftime('%Y-%m-%d')} "
        f"{side}"
    )

print()

print("=== 交互タッチ ===")

for date, side in alternating_touches:
    print(
        f"{date.strftime('%Y-%m-%d')} "
        f"{side}"
    )

print()

print("=== 結果 ===")
print(f"全タッチ数       : {len(touches):4d} 回")
print(f"交互タッチ数     : {len(alternating_touches):4d} 回")
print(f"上下切り替わり数 : {switch_count:4d} 回")