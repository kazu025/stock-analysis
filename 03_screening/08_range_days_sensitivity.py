"""
観測期間(RANGE_DAYS)を変化させて、
うねり検出の感度を比較する。

目的:
1. Zone Ratioは25%に固定する
2. 観測期間を40 / 60 / 80 / 100営業日に変化させる
3. 各期間について高値・安値からレンジを求める
4. Upper / Lower Zoneへの進入を検出する
5. 上下切り替わり数(Switch)を比較する
6. RANGE_DAYS=60が妥当か検証する

注意:
観測期間を変更すると、
単に使用する日数だけでなくRange High / Lowも変化する。
そのためUpper / Lower Zoneの価格そのものも期間ごとに変化する。
"""

import yfinance as yf


# --------------------------------------------------
# 1. 分析条件
# --------------------------------------------------

RANGE_DAYS_LIST = [
    40,
    60,
    80,
    100,
]

ZONE_RATIO = 0.25


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
# 3. 指定期間のSwitch数を計算する関数
# --------------------------------------------------

def calculate_range_result(
    df,
    range_days,
    zone_ratio
):

    # --------------------------------------------------
    # 指定営業日数を取り出す
    # --------------------------------------------------

    df_range = (
        df.tail(range_days)
        .copy()
    )


    # --------------------------------------------------
    # Range High / Low
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
    # Upper / Lower Zone
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
    # Zone到達判定
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
    # Zoneへ入った瞬間を検出
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
    # Touchを時系列順に保存
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
    # 同じ側への連続Touchをまとめる
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


    # --------------------------------------------------
    # 結果を返す
    # --------------------------------------------------

    return {
        "range_pct": range_pct,
        "range_high": range_high,
        "range_low": range_low,
        "upper_zone": upper_zone,
        "lower_zone": lower_zone,
        "switch": switch_count,
    }


# --------------------------------------------------
# 4. 全銘柄を分析する
# --------------------------------------------------

results = []

required_days = max(
    RANGE_DAYS_LIST
)

for ticker, name in stocks.items():

    print(
        f"分析中: {ticker} {name}"
    )

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    if len(df) < required_days:

        print(
            f"  データ不足: {len(df)}件"
        )

        continue


    # --------------------------------------------------
    # 各観測期間を分析
    # --------------------------------------------------

    period_results = {}

    for range_days in RANGE_DAYS_LIST:

        period_result = (
            calculate_range_result(
                df,
                range_days,
                ZONE_RATIO
            )
        )

        period_results[
            range_days
        ] = period_result


    # --------------------------------------------------
    # 銘柄ごとの結果を保存
    # --------------------------------------------------

    results.append(
        {
            "ticker": ticker,
            "name": name,
            "periods": period_results,
        }
    )


# --------------------------------------------------
# 5. 60日Switchの多い順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (
        x["periods"][60]["switch"],
        x["periods"][60]["range_pct"]
    ),
    reverse=True
)


# --------------------------------------------------
# 6. Switch感度分析を表示
# --------------------------------------------------

print()
print(
    "=== RANGE_DAYS 感度分析 "
    f"(ZONE_RATIO={ZONE_RATIO:.2f}) ==="
)
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'40日':>6s} "
    f"{'60日':>6s} "
    f"{'80日':>6s} "
    f"{'100日':>6s}"
)

print("-" * 52)


for result in results:

    periods = result["periods"]

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{periods[40]['switch']:6d} "
        f"{periods[60]['switch']:6d} "
        f"{periods[80]['switch']:6d} "
        f"{periods[100]['switch']:6d}"
    )


# --------------------------------------------------
# 7. Range%も表示する
# --------------------------------------------------

print()
print("=== Range% の変化 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'40日':>8s} "
    f"{'60日':>8s} "
    f"{'80日':>8s} "
    f"{'100日':>8s}"
)

print("-" * 60)


for result in results:

    periods = result["periods"]

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{periods[40]['range_pct']:7.1f}% "
        f"{periods[60]['range_pct']:7.1f}% "
        f"{periods[80]['range_pct']:7.1f}% "
        f"{periods[100]['range_pct']:7.1f}%"
    )


# --------------------------------------------------
# 8. 40日 → 100日のSwitch変化を表示
# --------------------------------------------------

print()
print("=== 40日 → 100日 Switch変化 ===")
print()

for result in results:

    switch40 = (
        result["periods"][40]["switch"]
    )

    switch100 = (
        result["periods"][100]["switch"]
    )

    difference = (
        switch100 - switch40
    )

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{switch40:2d} → "
        f"{switch100:2d} "
        f"(差 {difference:+d})"
    )