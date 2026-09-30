"""
塩野義製薬（4507）の株価レンジを期間別に比較する。

目的:
1. 過去2年間の株価を取得する
2. 20・40・60・100・250営業日について高値と安値を求める
3. 各期間の値幅率を計算する
4. うねり投資で使う分析期間を検討する

250営業日の高値・安値だけでは現在の値動きを
正しく表せない可能性があるため、複数期間を比較する。
"""

import yfinance as yf


TICKER = "4507.T"
SYMBOL_NAME = "塩野義製薬"

# 比較する営業日数
RANGE_DAYS = [20, 40, 60, 100, 250]


# --------------------------------------------------
# 1. 過去2年間の株価を取得する
# --------------------------------------------------

stock = yf.Ticker(TICKER)

df = stock.history(
    period="2y",
    auto_adjust=False
)


# --------------------------------------------------
# 2. 各期間の高値・安値・値幅率を計算する
# --------------------------------------------------

print("=== 株価レンジ比較 ===")
print(f"銘柄 : {SYMBOL_NAME} ({TICKER})")
print()

print("期間        安値        高値        値幅       値幅率")
print("-" * 58)

for days in RANGE_DAYS:

    # 直近days営業日を取り出す
    df_range = df.tail(days)

    # 期間内の最高値と最安値
    high = df_range["High"].max()
    low = df_range["Low"].min()

    # 値幅
    price_range = high - low

    # 安値に対する値幅の割合
    range_pct = price_range / low * 100

    print(
        f"{days:3d}日"
        f"  {low:10.1f}"
        f"  {high:10.1f}"
        f"  {price_range:10.1f}"
        f"  {range_pct:9.1f} %"
    )