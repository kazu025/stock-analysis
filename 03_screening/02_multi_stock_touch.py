"""
複数の日本株について、直近60営業日の値幅と
上下ゾーンへの交互タッチ回数を一括分析する。

目的:
1. 複数銘柄の直近60営業日の高値・安値を求める
2. 値幅率を計算する
3. レンジの上側20%・下側20%をゾーンとして定義する
4. High / Lowを使ってゾーンへのタッチを検出する
5. 同じ側への連続タッチをまとめる
6. 値幅だけでなく、上下を繰り返しているか比較する
"""

import yfinance as yf


RANGE_DAYS = 60
ZONE_RATIO = 0.20


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

    if len(df) < RANGE_DAYS:
        print(
            f"{ticker} {name}: "
            f"データ不足 ({len(df)}件)"
        )
        continue

    df_range = df.tail(RANGE_DAYS).copy()


    # --------------------------------------------------
    # 3. レンジを計算する
    # --------------------------------------------------

    range_high = df_range["High"].max()
    range_low = df_range["Low"].min()

    price_range = range_high - range_low

    range_pct = (
        price_range / range_low * 100
    )


    # --------------------------------------------------
    # 4. 上側・下側ゾーンを計算する
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
    # 5. High / Lowでゾーン到達を判定する
    # --------------------------------------------------

    df_range["UpperZone"] = (
        df_range["High"] >= upper_zone
    )

    df_range["LowerZone"] = (
        df_range["Low"] <= lower_zone
    )


    # --------------------------------------------------
    # 6. ゾーンへの進入を検出する
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
    # 7. タッチを時系列順に取り出す
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
    # 8. 同じ側への連続タッチをまとめる
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
    # 9. 上下切り替わり数を求める
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
    # 10. 結果を保存する
    # --------------------------------------------------

    results.append(
        (
            ticker,
            name,
            range_pct,
            touch_count,
            alternating_count,
            switch_count
        )
    )


# --------------------------------------------------
# 11. 上下切り替わり数が多い順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (x[5], x[2]),
    reverse=True
)


# --------------------------------------------------
# 12. 結果を表示する
# --------------------------------------------------

print()
print("=== 複数銘柄 うねり比較 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Range%':>8s} "
    f"{'Touch':>7s} "
    f"{'Alt':>6s} "
    f"{'Switch':>8s}"
)

print("-" * 58)

for (
    ticker,
    name,
    range_pct,
    touch_count,
    alternating_count,
    switch_count
) in results:

    print(
        f"{ticker:10s} "
        f"{name:10s} "
        f"{range_pct:7.1f}% "
        f"{touch_count:7d} "
        f"{alternating_count:6d} "
        f"{switch_count:8d}"
    )