"""
株価データから「うねり」を分析する共通処理。

主な機能:
1. 指定した期間の高値・安値からRangeを求める
2. Range幅を百分率で求める
3. 指定したZone RatioからUpper / Lower Zoneを求める
4. High / LowがZoneへ入った瞬間(Touch)を検出する
5. 同じ側への連続Touchをまとめる
6. Upper / Lowerの切り替わり回数(Switch Count)を求める

このモジュールは銘柄の選別(PASS / FAIL)を行わない。
「測定」だけを担当する。

例:
    result = calculate_wave(
        df,
        range_days=60,
        zone_ratio=0.25
    )

    print(result["range_pct"])
    print(result["switch_count"])
"""


def calculate_wave(
    df,
    range_days,
    zone_ratio
):
    """
    指定期間・Zone Ratioで株価のうねりを分析する。

    Parameters
    ----------
    df : pandas.DataFrame
        yfinanceなどから取得した株価データ。
        High / Low列が必要。

    range_days : int
        分析対象とする営業日数。
        例: 60

    zone_ratio : float
        Rangeの上下何割をZoneとするか。
        例: 0.25

    Returns
    -------
    dict
        range_high
        range_low
        price_range
        range_pct
        upper_zone
        lower_zone
        touch_count
        alternating_touch_count
        switch_count
        alternating_touches
    """

    # --------------------------------------------------
    # 1. 入力チェック
    # --------------------------------------------------

    if range_days <= 0:
        raise ValueError(
            "range_daysは1以上を指定してください"
        )

    if not (0.0 < zone_ratio < 0.5):
        raise ValueError(
            "zone_ratioは0より大きく0.5未満を指定してください"
        )

    if len(df) < range_days:
        raise ValueError(
            f"株価データが不足しています: "
            f"必要={range_days}日 "
            f"実際={len(df)}日"
        )

    if "High" not in df.columns:
        raise ValueError(
            "株価データにHigh列がありません"
        )

    if "Low" not in df.columns:
        raise ValueError(
            "株価データにLow列がありません"
        )


    # --------------------------------------------------
    # 2. 指定営業日数を取り出す
    # --------------------------------------------------

    df_range = (
        df.tail(range_days)
        .copy()
    )


    # --------------------------------------------------
    # 3. Range High / Low
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


    # --------------------------------------------------
    # 4. Range%
    #
    # LowからHighまで何%動いたか
    # --------------------------------------------------

    if range_low <= 0:
        raise ValueError(
            "range_lowが0以下のため"
            "Range%を計算できません"
        )

    range_pct = (
        price_range
        / range_low
        * 100
    )


    # --------------------------------------------------
    # 5. Upper / Lower Zone
    #
    # 例:
    #
    # High -------------------------
    #        Upper Zone
    # Upper ------------------------
    #
    #
    # Lower ------------------------
    #        Lower Zone
    # Low  -------------------------
    #
    # zone_ratio = 0.25なら
    # 上下それぞれRangeの25%をZoneとする。
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
    # 6. Zone内に入っている日を判定
    #
    # Upper:
    #   High >= upper_zone
    #
    # Lower:
    #   Low <= lower_zone
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
    # 7. Zoneへ「入った瞬間」を検出
    #
    # False → True
    #
    # GPIOで考えれば立ち上がりエッジ検出に近い。
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
    # 8. Touchを時系列順に保存
    #
    # 例:
    #
    # [
    #   (date1, "LOWER"),
    #   (date2, "UPPER"),
    #   (date3, "LOWER"),
    # ]
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
    # 9. 同じ側への連続Touchをまとめる
    #
    # LOWER
    # LOWER
    # LOWER
    # UPPER
    #
    # ↓
    #
    # LOWER
    # UPPER
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
    # 10. Switch Count
    #
    # LOWER → UPPER → LOWER
    #
    # Touch数  = 3
    # Switch数 = 2
    # --------------------------------------------------

    switch_count = max(
        0,
        len(alternating_touches) - 1
    )


    # --------------------------------------------------
    # 11. 分析結果を返す
    # --------------------------------------------------

    return {
        "range_days":
            range_days,

        "zone_ratio":
            zone_ratio,

        "range_high":
            range_high,

        "range_low":
            range_low,

        "price_range":
            price_range,

        "range_pct":
            range_pct,

        "upper_zone":
            upper_zone,

        "lower_zone":
            lower_zone,

        "touch_count":
            len(touches),

        "alternating_touch_count":
            len(alternating_touches),

        "switch_count":
            switch_count,

        "alternating_touches":
            alternating_touches,
    }