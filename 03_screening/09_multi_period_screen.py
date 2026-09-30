"""
複数期間のSwitch、60日Range、MA25・MA75を統合して
うねり投資候補を比較する。

目的:
1. 40 / 60 / 80 / 100営業日のSwitch数を計算する
2. Zone Ratioは25%に固定する
3. 60営業日のRange%を計算する
4. MA25 / MA75の20営業日変化率を計算する
5. 複数の特徴量を1つの表にまとめる
6. 単一期間だけでなく、複数期間での「うねり」を比較する

現段階ではPASS / FAILを決めず、
各特徴量を観察するための分析表として使用する。
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

MAIN_RANGE_DAYS = 60

ZONE_RATIO = 0.25

MA25_DAYS = 25
MA75_DAYS = 75

MA_COMPARE_DAYS = 20


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
# 3. 指定期間のRangeとSwitchを計算する
# --------------------------------------------------

def calculate_wave(
    df,
    range_days,
    zone_ratio
):

    df_range = (
        df.tail(range_days)
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
    # Zoneへの進入を検出
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
    # Touchを時系列順に取り出す
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


    return {
        "range_pct": range_pct,
        "range_high": range_high,
        "range_low": range_low,
        "upper_zone": upper_zone,
        "lower_zone": lower_zone,
        "switch": switch_count,
    }


# --------------------------------------------------
# 4. MA変化率を計算する
# --------------------------------------------------

def calculate_ma_change(df):

    df_ma = df.copy()


    # --------------------------------------------------
    # MA25
    # --------------------------------------------------

    df_ma["MA25"] = (
        df_ma["Close"]
        .rolling(MA25_DAYS)
        .mean()
    )


    # --------------------------------------------------
    # MA75
    # --------------------------------------------------

    df_ma["MA75"] = (
        df_ma["Close"]
        .rolling(MA75_DAYS)
        .mean()
    )


    # --------------------------------------------------
    # 現在値
    # --------------------------------------------------

    ma25_current = (
        df_ma["MA25"].iloc[-1]
    )

    ma75_current = (
        df_ma["MA75"].iloc[-1]
    )


    # --------------------------------------------------
    # 20営業日前
    # --------------------------------------------------

    ma25_previous = (
        df_ma["MA25"].iloc[
            -1 - MA_COMPARE_DAYS
        ]
    )

    ma75_previous = (
        df_ma["MA75"].iloc[
            -1 - MA_COMPARE_DAYS
        ]
    )


    # --------------------------------------------------
    # 変化率
    # --------------------------------------------------

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


    return (
        ma25_change_pct,
        ma75_change_pct
    )


# --------------------------------------------------
# 5. 全銘柄を分析する
# --------------------------------------------------

results = []

required_days = max(
    max(RANGE_DAYS_LIST),
    MA75_DAYS + MA_COMPARE_DAYS
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


    # --------------------------------------------------
    # データ数チェック
    # --------------------------------------------------

    if len(df) < required_days:

        print(
            f"  データ不足: {len(df)}件"
        )

        continue


    # --------------------------------------------------
    # 複数期間のWaveを計算
    # --------------------------------------------------

    wave_results = {}

    for range_days in RANGE_DAYS_LIST:

        wave_results[
            range_days
        ] = calculate_wave(
            df,
            range_days,
            ZONE_RATIO
        )


    # --------------------------------------------------
    # MA変化率
    # --------------------------------------------------

    (
        ma25_change_pct,
        ma75_change_pct
    ) = calculate_ma_change(df)


    # --------------------------------------------------
    # 60日Range%
    # --------------------------------------------------

    range60_pct = (
        wave_results[
            MAIN_RANGE_DAYS
        ]["range_pct"]
    )


    # --------------------------------------------------
    # 結果を保存
    # --------------------------------------------------

    results.append(
        {
            "ticker": ticker,
            "name": name,

            "range60": range60_pct,

            "switch40":
                wave_results[40]["switch"],

            "switch60":
                wave_results[60]["switch"],

            "switch80":
                wave_results[80]["switch"],

            "switch100":
                wave_results[100]["switch"],

            "ma25":
                ma25_change_pct,

            "ma75":
                ma75_change_pct,
        }
    )


# --------------------------------------------------
# 6. 60日Switchを中心に並べる
#
# 第1キー : Switch60
# 第2キー : Switch40
# 第3キー : Range60
# --------------------------------------------------

results.sort(
    key=lambda x: (
        x["switch60"],
        x["switch40"],
        x["range60"]
    ),
    reverse=True
)


# --------------------------------------------------
# 7. 統合結果を表示する
# --------------------------------------------------

print()
print(
    "=== Multi Period Wave Screening ==="
)
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'R60%':>7s} "
    f"{'S40':>4s} "
    f"{'S60':>4s} "
    f"{'S80':>4s} "
    f"{'S100':>5s} "
    f"{'MA25%':>8s} "
    f"{'MA75%':>8s}"
)

print("-" * 78)


for result in results:

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{result['range60']:6.1f}% "
        f"{result['switch40']:4d} "
        f"{result['switch60']:4d} "
        f"{result['switch80']:4d} "
        f"{result['switch100']:5d} "
        f"{result['ma25']:+7.2f}% "
        f"{result['ma75']:+7.2f}%"
    )


# --------------------------------------------------
# 8. 60日Switch >= 3 の銘柄を表示する
#
# これはPASS / FAILではなく、
# 「最近60日で往復性が強い銘柄」の確認用。
# --------------------------------------------------

print()
print(
    "=== Switch60 >= 3 ==="
)
print()


candidate_count = 0


for result in results:

    if result["switch60"] >= 3:

        candidate_count += 1

        print(
            f"{result['ticker']:10s} "
            f"{result['name']:10s} "
            f"R60={result['range60']:5.1f}% "
            f"S40={result['switch40']:2d} "
            f"S60={result['switch60']:2d} "
            f"S80={result['switch80']:2d} "
            f"S100={result['switch100']:2d} "
            f"MA25={result['ma25']:+6.2f}% "
            f"MA75={result['ma75']:+6.2f}%"
        )


print()

print(
    f"候補数 : "
    f"{candidate_count} / "
    f"{len(results)} 銘柄"
)