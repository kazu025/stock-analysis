"""
複数の日本株について、直近60営業日の値幅・交互タッチ回数と、
25日・75日移動平均の変化率を一括分析する。

目的:
1. 直近60営業日の値幅率を計算する
2. High / Lowを使って上下ゾーンへのタッチを検出する
3. 同じ側への連続タッチをまとめ、上下切り替わり数を求める
4. MA25・MA75の20営業日前からの変化率を計算する
5. 「値幅」「往復」「トレンド」の3つを比較する

MA変化率:
    正の値  : 移動平均が上向き
    負の値  : 移動平均が下向き
    0%付近  : 移動平均が比較的横ばい
"""

import yfinance as yf


RANGE_DAYS = 60
ZONE_RATIO = 0.20

MA25_DAYS = 25
MA75_DAYS = 75
COMPARE_DAYS = 20


# --------------------------------------------------
# 1. 分析対象銘柄
# --------------------------------------------------

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
# 2. 各銘柄を分析する
# --------------------------------------------------

results = []

for ticker, name in stocks.items():

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    # MA75と20営業日前を比較するため、
    # 最低でも 75 + 20 営業日程度必要
    required_days = MA75_DAYS + COMPARE_DAYS

    if len(df) < required_days:
        print(
            f"{ticker} {name}: "
            f"データ不足 ({len(df)}件)"
        )
        continue


    # --------------------------------------------------
    # 3. 移動平均を計算する
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
    # 4. MAの20営業日前からの変化率
    # --------------------------------------------------

    ma25_current = df["MA25"].iloc[-1]

    ma25_previous = (
        df["MA25"].iloc[-1 - COMPARE_DAYS]
    )

    ma75_current = df["MA75"].iloc[-1]

    ma75_previous = (
        df["MA75"].iloc[-1 - COMPARE_DAYS]
    )

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
    # 5. 直近60営業日を取り出す
    # --------------------------------------------------

    df_range = df.tail(RANGE_DAYS).copy()


    # --------------------------------------------------
    # 6. レンジを計算する
    # --------------------------------------------------

    range_high = df_range["High"].max()
    range_low = df_range["Low"].min()

    price_range = range_high - range_low

    range_pct = (
        price_range / range_low * 100
    )


    # --------------------------------------------------
    # 7. 上側・下側ゾーンを計算する
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
    # 8. High / Lowでゾーン到達を判定する
    # --------------------------------------------------

    df_range["UpperZone"] = (
        df_range["High"] >= upper_zone
    )

    df_range["LowerZone"] = (
        df_range["Low"] <= lower_zone
    )


    # --------------------------------------------------
    # 9. ゾーンへの進入を検出する
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
    # 10. タッチを時系列順に取り出す
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
    # 11. 同じ側への連続タッチをまとめる
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
    # 12. 上下切り替わり数を求める
    # --------------------------------------------------

    touch_count = len(touches)

    alternating_count = len(
        alternating_touches
    )

    switch_count = max(
        0,
        alternating_count - 1
    )


    # --------------------------------------------------
    # 13. 結果を保存する
    # --------------------------------------------------

    results.append(
        (
            ticker,
            name,
            range_pct,
            touch_count,
            alternating_count,
            switch_count,
            ma25_change_pct,
            ma75_change_pct
        )
    )


# --------------------------------------------------
# 14. 上下切り替わり数が多い順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (x[5], x[2]),
    reverse=True
)


# --------------------------------------------------
# 15. 結果を表示する
# --------------------------------------------------

print()
print("=== 複数銘柄 うねり + 移動平均比較 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Range%':>8s} "
    f"{'Touch':>6s} "
    f"{'Alt':>5s} "
    f"{'Switch':>7s} "
    f"{'MA25%':>8s} "
    f"{'MA75%':>8s}"
)

print("-" * 78)

for (
    ticker,
    name,
    range_pct,
    touch_count,
    alternating_count,
    switch_count,
    ma25_change_pct,
    ma75_change_pct
) in results:

    print(
        f"{ticker:10s} "
        f"{name:10s} "
        f"{range_pct:7.1f}% "
        f"{touch_count:6d} "
        f"{alternating_count:5d} "
        f"{switch_count:7d} "
        f"{ma25_change_pct:+7.2f}% "
        f"{ma75_change_pct:+7.2f}%"
    )