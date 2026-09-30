"""
screening_core.py の calculate_wave() の動作確認。

目的:
1. 塩野義製薬(4507.T)の株価データを取得する
2. 60営業日・Zone Ratio 25%でうねりを分析する
3. Range%とSwitch Countを表示する
4. 09_multi_period_screen.pyまでの計算結果と一致することを確認する

期待値:
    Range%      : 約12.9%
    Switch Count: 4

※株価データが更新されると、期待値は変化する可能性がある。
"""

import yfinance as yf

from screening_core import calculate_wave


# --------------------------------------------------
# 1. テスト対象
# --------------------------------------------------

TICKER = "4507.T"
NAME = "塩野義製薬"

RANGE_DAYS = 60
ZONE_RATIO = 0.25


# --------------------------------------------------
# 2. 株価データ取得
# --------------------------------------------------

print(
    f"株価データ取得: "
    f"{TICKER} {NAME}"
)

stock = yf.Ticker(TICKER)

df = stock.history(
    period="2y",
    auto_adjust=False
)


# --------------------------------------------------
# 3. screening_coreで分析
# --------------------------------------------------

result = calculate_wave(
    df,
    range_days=RANGE_DAYS,
    zone_ratio=ZONE_RATIO
)


# --------------------------------------------------
# 4. 分析結果表示
# --------------------------------------------------

print()
print("=== screening_core 動作確認 ===")
print()

print(
    f"銘柄             : "
    f"{TICKER} {NAME}"
)

print(
    f"分析期間         : "
    f"{result['range_days']}営業日"
)

print(
    f"Zone Ratio       : "
    f"{result['zone_ratio']:.2f}"
)

print()

print(
    f"Range Low        : "
    f"{result['range_low']:.1f}"
)

print(
    f"Range High       : "
    f"{result['range_high']:.1f}"
)

print(
    f"Price Range      : "
    f"{result['price_range']:.1f}"
)

print(
    f"Range%           : "
    f"{result['range_pct']:.1f}%"
)

print()

print(
    f"Upper Zone       : "
    f"{result['upper_zone']:.1f}"
)

print(
    f"Lower Zone       : "
    f"{result['lower_zone']:.1f}"
)

print()

print(
    f"Touch Count      : "
    f"{result['touch_count']}"
)

print(
    f"Alternating Touch: "
    f"{result['alternating_touch_count']}"
)

print(
    f"Switch Count     : "
    f"{result['switch_count']}"
)


# --------------------------------------------------
# 5. Alternating Touchの内容を表示
# --------------------------------------------------

print()
print("=== Alternating Touch ===")
print()

for date, side in result["alternating_touches"]:

    print(
        f"{date.strftime('%Y-%m-%d')} "
        f"{side}"
    )


# --------------------------------------------------
# 6. 期待値との比較
# --------------------------------------------------

print()
print("=== 従来結果との比較 ===")
print()

EXPECTED_RANGE_PCT = 12.9
EXPECTED_SWITCH_COUNT = 4

range_difference = abs(
    result["range_pct"]
    - EXPECTED_RANGE_PCT
)

range_ok = (
    range_difference < 0.2
)

switch_ok = (
    result["switch_count"]
    == EXPECTED_SWITCH_COUNT
)


print(
    f"Range% : "
    f"{result['range_pct']:.1f}% "
    f"(期待 約{EXPECTED_RANGE_PCT:.1f}%) "
    f"{'OK' if range_ok else 'CHECK'}"
)

print(
    f"Switch : "
    f"{result['switch_count']} "
    f"(期待 {EXPECTED_SWITCH_COUNT}) "
    f"{'OK' if switch_ok else 'CHECK'}"
)


# --------------------------------------------------
# 7. 最終判定
# --------------------------------------------------

print()

if range_ok and switch_ok:

    print(
        "RESULT: OK "
        "- screening_coreは従来結果と一致"
    )

else:

    print(
        "RESULT: CHECK "
        "- 従来結果との差を確認してください"
    )