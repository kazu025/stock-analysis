"""
塩野義製薬（4507）の直近60営業日について、
ゾーンへのタッチ判定に使う価格を比較する。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. レンジの上側20%・下側20%をゾーンとして定義する
3. Closeを使ったタッチ回数を求める
4. High / Lowを使ったタッチ回数を求める
5. 2つの判定方法を比較する

Close判定:
    上側 : Close >= 上側境界
    下側 : Close <= 下側境界

High / Low判定:
    上側 : High >= 上側境界
    下側 : Low <= 下側境界
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
# 5. Closeを使ってゾーンを判定する
# --------------------------------------------------

df_range["UpperClose"] = df_range["Close"] >= upper_zone
df_range["LowerClose"] = df_range["Close"] <= lower_zone


# --------------------------------------------------
# 6. High / Lowを使ってゾーンを判定する
# --------------------------------------------------

df_range["UpperHigh"] = df_range["High"] >= upper_zone
df_range["LowerLow"] = df_range["Low"] <= lower_zone


# --------------------------------------------------
# 7. Closeによるタッチを検出する
# --------------------------------------------------

df_range["UpperTouchClose"] = (
    df_range["UpperClose"]
    & ~df_range["UpperClose"].shift(1, fill_value=False)
)

df_range["LowerTouchClose"] = (
    df_range["LowerClose"]
    & ~df_range["LowerClose"].shift(1, fill_value=False)
)


# --------------------------------------------------
# 8. High / Lowによるタッチを検出する
# --------------------------------------------------

df_range["UpperTouchHigh"] = (
    df_range["UpperHigh"]
    & ~df_range["UpperHigh"].shift(1, fill_value=False)
)

df_range["LowerTouchLow"] = (
    df_range["LowerLow"]
    & ~df_range["LowerLow"].shift(1, fill_value=False)
)


# --------------------------------------------------
# 9. タッチ回数を数える
# --------------------------------------------------

upper_close_count = df_range["UpperTouchClose"].sum()
lower_close_count = df_range["LowerTouchClose"].sum()

upper_high_count = df_range["UpperTouchHigh"].sum()
lower_low_count = df_range["LowerTouchLow"].sum()


# --------------------------------------------------
# 10. 結果を表示する
# --------------------------------------------------

print("=== タッチ判定価格の比較 ===")
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

print("=== タッチ回数比較 ===")
print("判定方法           上側       下側")
print("----------------------------------")
print(
    f"Close             "
    f"{upper_close_count:4d} 回    "
    f"{lower_close_count:4d} 回"
)
print(
    f"High / Low        "
    f"{upper_high_count:4d} 回    "
    f"{lower_low_count:4d} 回"
)


# --------------------------------------------------
# 11. High / Lowでタッチした日を表示する
# --------------------------------------------------

print()
print("=== High / Lowでタッチした日 ===")

for date, row in df_range.iterrows():

    if row["UpperTouchHigh"]:
        print(
            f"{date.strftime('%Y-%m-%d')} "
            f"上側  "
            f"High={row['High']:8.1f} "
            f"Close={row['Close']:8.1f}"
        )

    if row["LowerTouchLow"]:
        print(
            f"{date.strftime('%Y-%m-%d')} "
            f"下側  "
            f"Low={row['Low']:8.1f} "
            f"Close={row['Close']:8.1f}"
        )