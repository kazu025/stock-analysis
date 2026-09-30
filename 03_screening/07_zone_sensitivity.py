"""
Upper / Lower Zoneの幅を変化させて、
うねり検出の感度を比較する。

目的:
1. 直近60営業日の高値・安値からレンジを求める
2. Zone Ratioを20% / 25% / 30%に変化させる
3. 各Zone RatioについてUpper / Lowerへの進入を検出する
4. 同じ側への連続タッチをまとめる
5. 上下切り替わり数(Switch)を比較する
6. ZONE_RATIO=0.20が厳しすぎないか確認する

Zone Ratio:
    0.20 : レンジ上側20% / 下側20%
    0.25 : レンジ上側25% / 下側25%
    0.30 : レンジ上側30% / 下側30%
"""

import yfinance as yf


# --------------------------------------------------
# 1. 分析条件
# --------------------------------------------------

RANGE_DAYS = 60

ZONE_RATIOS = [
    0.20,
    0.25,
    0.30,
]


# --------------------------------------------------
# 2. 分析対象銘柄
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
# 3. Switch数を計算する関数
# --------------------------------------------------

def calculate_switch_count(
    df_range,
    range_high,
    range_low,
    zone_ratio
):

    price_range = (
        range_high - range_low
    )


    # --------------------------------------------------
    # Upper / Lower Zone境界
    # --------------------------------------------------

    upper_zone = (
        range_high
        - price_range * zone_ratio
    )

    lower_zone = (
        range_low
        + price_range * zone_ratio
    )


    # --------------------------------------------------
    # High / LowでZone到達を判定
    # --------------------------------------------------

    upper_zone_hit = (
        df_range["High"]
        >= upper_zone
    )

    lower_zone_hit = (
        df_range["Low"]
        <= lower_zone
    )


    # --------------------------------------------------
    # Zoneの外側から内側へ入った瞬間を検出
    # --------------------------------------------------

    upper_touch = (
        upper_zone_hit
        & ~upper_zone_hit.shift(
            1,
            fill_value=False
        )
    )

    lower_touch = (
        lower_zone_hit
        & ~lower_zone_hit.shift(
            1,
            fill_value=False
        )
    )


    # --------------------------------------------------
    # タッチを時系列順に取り出す
    # --------------------------------------------------

    touches = []

    for date in df_range.index:

        if upper_touch.loc[date]:
            touches.append(
                (date, "UPPER")
            )

        if lower_touch.loc[date]:
            touches.append(
                (date, "LOWER")
            )


    # --------------------------------------------------
    # 同じ側への連続タッチをまとめる
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
    # Switch数
    # --------------------------------------------------

    switch_count = max(
        0,
        len(alternating_touches) - 1
    )

    return switch_count


# --------------------------------------------------
# 4. 全銘柄を分析する
# --------------------------------------------------

results = []

for ticker, name in stocks.items():

    print(
        f"分析中: {ticker} {name}"
    )

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    if len(df) < RANGE_DAYS:

        print(
            f"  データ不足: {len(df)}件"
        )

        continue


    # --------------------------------------------------
    # 直近60営業日
    # --------------------------------------------------

    df_range = (
        df.tail(RANGE_DAYS)
        .copy()
    )


    # --------------------------------------------------
    # Range
    # --------------------------------------------------

    range_high = (
        df_range["High"].max()
    )

    range_low = (
        df_range["Low"].min()
    )

    price_range = (
        range_high - range_low
    )

    range_pct = (
        price_range
        / range_low
        * 100
    )


    # --------------------------------------------------
    # 各Zone RatioでSwitch数を計算
    # --------------------------------------------------

    switch_counts = {}

    for zone_ratio in ZONE_RATIOS:

        switch_count = (
            calculate_switch_count(
                df_range,
                range_high,
                range_low,
                zone_ratio
            )
        )

        switch_counts[
            zone_ratio
        ] = switch_count


    # --------------------------------------------------
    # 結果を保存
    # --------------------------------------------------

    results.append(
        {
            "ticker": ticker,
            "name": name,
            "range_pct": range_pct,
            "switch_counts": switch_counts,
        }
    )


# --------------------------------------------------
# 5. Zone20のSwitch数が多い順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (
        x["switch_counts"][0.20],
        x["range_pct"]
    ),
    reverse=True
)


# --------------------------------------------------
# 6. 結果を表示する
# --------------------------------------------------

print()
print("=== Zone Ratio 感度分析 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Range%':>8s} "
    f"{'Zone20':>7s} "
    f"{'Zone25':>7s} "
    f"{'Zone30':>7s}"
)

print("-" * 62)


for result in results:

    switch_counts = (
        result["switch_counts"]
    )

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{result['range_pct']:7.1f}% "
        f"{switch_counts[0.20]:7d} "
        f"{switch_counts[0.25]:7d} "
        f"{switch_counts[0.30]:7d}"
    )


# --------------------------------------------------
# 7. Zoneを広げたときの増加量
# --------------------------------------------------

print()
print("=== Zone20 → Zone30 の変化 ===")
print()

for result in results:

    switch20 = (
        result["switch_counts"][0.20]
    )

    switch30 = (
        result["switch_counts"][0.30]
    )

    difference = (
        switch30 - switch20
    )

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{switch20:2d} → "
        f"{switch30:2d} "
        f"(差 {difference:+d})"
    )