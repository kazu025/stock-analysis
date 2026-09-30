"""
複数の日本株について、うねり投資候補を条件で絞り込む。

目的:
1. 直近60営業日の値幅率を計算する
2. High / Lowを使って上下ゾーンへのタッチを検出する
3. 上下切り替わり回数を求める
4. MA25・MA75の20営業日前からの変化率を計算する
5. 値幅・上下切り替わり・MAの傾きで候補を絞り込む
6. 各銘柄がどの条件を通過／不通過だったか表示する

現在の仮条件:
    値幅率       : 10%以上
    上下切替回数 : 2回以上
    MA25変化率   : -3% ～ +3%
    MA75変化率   : -3% ～ +3%

※ 閾値はまだ確定値ではない。
   実際のチャートと比較しながら今後調整する。
"""

import yfinance as yf


# --------------------------------------------------
# 1. 分析条件
# --------------------------------------------------

RANGE_DAYS = 60
ZONE_RATIO = 0.20

MA25_DAYS = 25
MA75_DAYS = 75
COMPARE_DAYS = 20


# --------------------------------------------------
# 2. スクリーニング条件
# --------------------------------------------------

MIN_RANGE_PCT = 10.0
MIN_SWITCH_COUNT = 2

MAX_ABS_MA25_PCT = 3.0
MAX_ABS_MA75_PCT = 3.0


# --------------------------------------------------
# 3. 分析対象銘柄
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
# 4. 各銘柄を分析する
# --------------------------------------------------

results = []

for ticker, name in stocks.items():

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    required_days = MA75_DAYS + COMPARE_DAYS

    if len(df) < required_days:
        print(
            f"{ticker} {name}: "
            f"データ不足 ({len(df)}件)"
        )
        continue


    # --------------------------------------------------
    # 5. 移動平均を計算する
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
    # 6. MA変化率を計算する
    # --------------------------------------------------

    ma25_current = df["MA25"].iloc[-1]
    ma25_previous = df["MA25"].iloc[-1 - COMPARE_DAYS]

    ma75_current = df["MA75"].iloc[-1]
    ma75_previous = df["MA75"].iloc[-1 - COMPARE_DAYS]

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
    # 7. 直近60営業日のレンジ
    # --------------------------------------------------

    df_range = df.tail(RANGE_DAYS).copy()

    range_high = df_range["High"].max()
    range_low = df_range["Low"].min()

    price_range = range_high - range_low

    range_pct = (
        price_range / range_low * 100
    )


    # --------------------------------------------------
    # 8. 上側・下側ゾーン
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
    # 9. High / Lowでゾーン到達を判定する
    # --------------------------------------------------

    df_range["UpperZone"] = (
        df_range["High"] >= upper_zone
    )

    df_range["LowerZone"] = (
        df_range["Low"] <= lower_zone
    )


    # --------------------------------------------------
    # 10. ゾーンへの進入を検出する
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
    # 11. タッチを時系列順に取り出す
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
    # 12. 同じ側への連続タッチをまとめる
    # --------------------------------------------------

    alternating_touches = []

    for date, side in touches:

        if len(alternating_touches) == 0:
            alternating_touches.append(
                (date, side)
            )
            continue

        previous_side = alternating_touches[-1][1]

        if side != previous_side:
            alternating_touches.append(
                (date, side)
            )


    # --------------------------------------------------
    # 13. 上下切り替わり数
    # --------------------------------------------------

    switch_count = max(
        0,
        len(alternating_touches) - 1
    )


    # --------------------------------------------------
    # 14. 各条件を判定する
    # --------------------------------------------------

    range_ok = (
        range_pct >= MIN_RANGE_PCT
    )

    switch_ok = (
        switch_count >= MIN_SWITCH_COUNT
    )

    ma25_ok = (
        abs(ma25_change_pct)
        <= MAX_ABS_MA25_PCT
    )

    ma75_ok = (
        abs(ma75_change_pct)
        <= MAX_ABS_MA75_PCT
    )


    # --------------------------------------------------
    # 15. 全条件を満たしたか
    # --------------------------------------------------

    candidate = (
        range_ok
        and switch_ok
        and ma25_ok
        and ma75_ok
    )


    # --------------------------------------------------
    # 16. 結果を保存する
    # --------------------------------------------------

    results.append(
        {
            "ticker": ticker,
            "name": name,

            "range_pct": range_pct,
            "switch": switch_count,

            "ma25": ma25_change_pct,
            "ma75": ma75_change_pct,

            "range_ok": range_ok,
            "switch_ok": switch_ok,
            "ma25_ok": ma25_ok,
            "ma75_ok": ma75_ok,

            "candidate": candidate,
        }
    )


# --------------------------------------------------
# 17. 候補を先頭に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: (
        x["candidate"],
        x["switch"],
        x["range_pct"]
    ),
    reverse=True
)


# --------------------------------------------------
# 18. 全銘柄の判定結果
# --------------------------------------------------

print()
print("=== うねり投資 スクリーニング ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Range%':>8s} "
    f"{'Switch':>7s} "
    f"{'MA25%':>8s} "
    f"{'MA75%':>8s} "
    f"{'Result':>8s}"
)

print("-" * 78)

for result in results:

    if result["candidate"]:
        status = "PASS"
    else:
        status = "FAIL"

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"{result['range_pct']:7.1f}% "
        f"{result['switch']:7d} "
        f"{result['ma25']:+7.2f}% "
        f"{result['ma75']:+7.2f}% "
        f"{status:>8s}"
    )


# --------------------------------------------------
# 19. 不通過理由を表示する
# --------------------------------------------------

print()
print("=== 不通過理由 ===")
print()

for result in results:

    if result["candidate"]:
        continue

    reasons = []

    if not result["range_ok"]:
        reasons.append("値幅不足")

    if not result["switch_ok"]:
        reasons.append("上下切替不足")

    if not result["ma25_ok"]:
        reasons.append("MA25傾き大")

    if not result["ma75_ok"]:
        reasons.append("MA75傾き大")

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} : "
        + ", ".join(reasons)
    )


# --------------------------------------------------
# 20. 候補銘柄だけを表示する
# --------------------------------------------------

print()
print("=== 候補銘柄 ===")
print()

candidate_count = 0

for result in results:

    if not result["candidate"]:
        continue

    candidate_count += 1

    print(
        f"{result['ticker']:10s} "
        f"{result['name']:10s} "
        f"Range={result['range_pct']:5.1f}% "
        f"Switch={result['switch']:2d} "
        f"MA25={result['ma25']:+6.2f}% "
        f"MA75={result['ma75']:+6.2f}%"
    )

print()
print(
    f"候補数 : {candidate_count} / {len(results)} 銘柄"
)