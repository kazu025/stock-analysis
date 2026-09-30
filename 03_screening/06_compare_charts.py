"""
複数銘柄の60営業日チャートを一覧表示して、
うねり検出結果と実際の値動きを比較する。

目的:
1. 10銘柄を同じ条件で分析する
2. Range%・Switch・MA25・MA75を計算する
3. Upper / Lower Zoneを表示する
4. 交互タッチ位置を表示する
5. 複数銘柄を同じFigure上で比較する
6. Switch数が実際の「うねりらしさ」と一致するか確認する
"""

import yfinance as yf
import matplotlib.pyplot as plt


# --------------------------------------------------
# 1. 分析条件
# --------------------------------------------------

RANGE_DAYS = 60
ZONE_RATIO = 0.20

MA25_DAYS = 25
MA75_DAYS = 75
COMPARE_DAYS = 20


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
# 3. 1銘柄を分析する関数
# --------------------------------------------------

def analyze_stock(ticker, name):

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    required_days = (
        MA75_DAYS
        + COMPARE_DAYS
    )

    if len(df) < required_days:
        return None


    # --------------------------------------------------
    # 移動平均
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
    # MA変化率
    # --------------------------------------------------

    ma25_current = (
        df["MA25"].iloc[-1]
    )

    ma25_previous = (
        df["MA25"].iloc[
            -1 - COMPARE_DAYS
        ]
    )

    ma75_current = (
        df["MA75"].iloc[-1]
    )

    ma75_previous = (
        df["MA75"].iloc[
            -1 - COMPARE_DAYS
        ]
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
    # 直近60営業日
    # --------------------------------------------------

    df_range = (
        df.tail(RANGE_DAYS)
        .copy()
    )


    # --------------------------------------------------
    # レンジ
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
        - price_range * ZONE_RATIO
    )

    lower_zone = (
        range_low
        + price_range * ZONE_RATIO
    )


    # --------------------------------------------------
    # ゾーン到達判定
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
    # ゾーンへの進入を検出
    # --------------------------------------------------

    df_range["UpperTouch"] = (
        df_range["UpperZone"]
        & ~df_range[
            "UpperZone"
        ].shift(
            1,
            fill_value=False
        )
    )

    df_range["LowerTouch"] = (
        df_range["LowerZone"]
        & ~df_range[
            "LowerZone"
        ].shift(
            1,
            fill_value=False
        )
    )


    # --------------------------------------------------
    # タッチを時系列順に取り出す
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


    # --------------------------------------------------
    # 分析結果を辞書で返す
    # --------------------------------------------------

    return {
        "ticker": ticker,
        "name": name,

        "df": df_range,

        "range_high": range_high,
        "range_low": range_low,

        "upper_zone": upper_zone,
        "lower_zone": lower_zone,

        "range_pct": range_pct,

        "switch": switch_count,

        "ma25": ma25_change_pct,
        "ma75": ma75_change_pct,

        "touches": alternating_touches,
    }


# --------------------------------------------------
# 4. 全銘柄を分析する
# --------------------------------------------------

results = []

for ticker, name in stocks.items():

    print(
        f"分析中: {ticker} {name}"
    )

    result = analyze_stock(
        ticker,
        name
    )

    if result is not None:
        results.append(result)


# --------------------------------------------------
# 5. Switchの多い順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (
        x["switch"],
        x["range_pct"]
    ),
    reverse=True
)


# --------------------------------------------------
# 6. コンソールに一覧表示
# --------------------------------------------------

print()
print("=== 比較結果 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Range%':>8s} "
    f"{'Switch':>7s} "
    f"{'MA25%':>8s} "
    f"{'MA75%':>8s}"
)

print("-" * 70)

for result in results:

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{result['range_pct']:7.1f}% "
        f"{result['switch']:7d} "
        f"{result['ma25']:+7.2f}% "
        f"{result['ma75']:+7.2f}%"
    )


# --------------------------------------------------
# 7. Figureを作成する
# --------------------------------------------------

figure, axes = plt.subplots(
    5,
    2,
    figsize=(16, 20)
)

axes = axes.flatten()


# --------------------------------------------------
# 8. 各銘柄を描画する
# --------------------------------------------------

for ax, result in zip(
    axes,
    results
):

    df_range = result["df"]


    # --------------------------------------------------
    # 終値
    # --------------------------------------------------

    ax.plot(
        df_range.index,
        df_range["Close"],
        label="Close",
        linewidth=1.5
    )


    # --------------------------------------------------
    # MA25
    # --------------------------------------------------

    ax.plot(
        df_range.index,
        df_range["MA25"],
        label="MA25",
        linewidth=1.0
    )


    # --------------------------------------------------
    # MA75
    # --------------------------------------------------

    ax.plot(
        df_range.index,
        df_range["MA75"],
        label="MA75",
        linewidth=1.0
    )


    # --------------------------------------------------
    # Upper Zone
    # --------------------------------------------------

    ax.axhline(
        result["upper_zone"],
        linestyle=":",
        linewidth=1.0,
        label="Upper Zone"
    )


    # --------------------------------------------------
    # Lower Zone
    # --------------------------------------------------

    ax.axhline(
        result["lower_zone"],
        linestyle=":",
        linewidth=1.0,
        label="Lower Zone"
    )


    # --------------------------------------------------
    # 交互タッチ位置
    # --------------------------------------------------

    for date, side in result["touches"]:

        row = df_range.loc[date]

        if side == "UPPER":

            price = row["High"]

            ax.scatter(
                date,
                price,
                marker="v",
                s=45,
                zorder=5
            )

        else:

            price = row["Low"]

            ax.scatter(
                date,
                price,
                marker="^",
                s=45,
                zorder=5
            )


    # --------------------------------------------------
    # タイトル
    # --------------------------------------------------

    ax.set_title(
        f"{result['name']} "
        f"({result['ticker']})\n"
        f"Range={result['range_pct']:.1f}%  "
        f"Switch={result['switch']}  "
        f"MA25={result['ma25']:+.2f}%  "
        f"MA75={result['ma75']:+.2f}%"
    )


    # --------------------------------------------------
    # グリッド
    # --------------------------------------------------

    ax.grid(
        True,
        alpha=0.3
    )


    # --------------------------------------------------
    # 凡例
    # --------------------------------------------------

    ax.legend(
        fontsize=7
    )


# --------------------------------------------------
# 9. 全体タイトル
# --------------------------------------------------

figure.suptitle(
    "Wave Screening - 60 Trading Days",
    fontsize=16
)


# --------------------------------------------------
# 10. レイアウト調整
# --------------------------------------------------

plt.tight_layout(
    rect=[0, 0, 1, 0.98]
)

plt.show()