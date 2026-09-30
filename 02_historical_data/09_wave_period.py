"""
塩野義製薬（4507）の直近60営業日について、
上側・下側ゾーンを移動するのに要した営業日数を調べる。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. High / Lowを使って上下ゾーンへのタッチを検出する
3. 同じ側への連続タッチをまとめる
4. LOWER → UPPER、UPPER → LOWERの移動に
   何営業日かかったかを計算する
5. うねりの周期を数値として確認する
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

    if len(alternating_touches) == 0:
        alternating_touches.append((date, side))
        continue

    previous_side = alternating_touches[-1][1]

    if side != previous_side:
        alternating_touches.append((date, side))


# --------------------------------------------------
# 9. 反対側ゾーンまでの営業日数を計算する
# --------------------------------------------------

wave_periods = []

for i in range(1, len(alternating_touches)):

    previous_date, previous_side = alternating_touches[i - 1]
    current_date, current_side = alternating_touches[i]

    previous_pos = df_range.index.get_loc(previous_date)
    current_pos = df_range.index.get_loc(current_date)

    trading_days = current_pos - previous_pos

    wave_periods.append(
        (
            previous_date,
            previous_side,
            current_date,
            current_side,
            trading_days
        )
    )


# --------------------------------------------------
# 10. 結果を表示する
# --------------------------------------------------

print("=== うねり周期分析 ===")
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

print("=== 交互タッチ ===")

for date, side in alternating_touches:
    print(
        f"{date.strftime('%Y-%m-%d')} "
        f"{side}"
    )

print()

print("=== ゾーン間の移動期間 ===")

for (
    previous_date,
    previous_side,
    current_date,
    current_side,
    trading_days
) in wave_periods:

    print(
        f"{previous_date.strftime('%Y-%m-%d')} "
        f"{previous_side:5s}"
        f" → "
        f"{current_date.strftime('%Y-%m-%d')} "
        f"{current_side:5s}"
        f" : {trading_days:3d} 営業日"
    )


# --------------------------------------------------
# 11. 平均移動期間を計算する
# --------------------------------------------------

if len(wave_periods) > 0:

    total_days = sum(
        period[4]
        for period in wave_periods
    )

    average_days = total_days / len(wave_periods)

    print()
    print("=== 周期集計 ===")
    print(f"上下切り替わり数 : {len(wave_periods):4d} 回")
    print(f"平均移動期間     : {average_days:6.1f} 営業日")