"""
複数の日本株について、直近60営業日の株価レンジを一括分析する。

目的:
1. 複数銘柄の株価をYahoo Financeから取得する
2. 各銘柄の直近60営業日の高値・安値を求める
3. 値幅と値幅率を計算する
4. 銘柄ごとの結果を一覧表示する

これまで塩野義製薬1銘柄で行っていた分析を、
複数銘柄へ展開する最初のステップとする。
"""

import yfinance as yf


RANGE_DAYS = 60


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
# 2. 各銘柄を順番に分析する
# --------------------------------------------------

results = []

for ticker, name in stocks.items():

    stock = yf.Ticker(ticker)

    df = stock.history(
        period="2y",
        auto_adjust=False
    )

    # データ取得に失敗した場合
    if len(df) < RANGE_DAYS:
        print(
            f"{ticker} {name}: "
            f"データ不足 ({len(df)}件)"
        )
        continue

    df_range = df.tail(RANGE_DAYS)

    range_high = df_range["High"].max()
    range_low = df_range["Low"].min()

    price_range = range_high - range_low

    range_pct = (
        price_range / range_low * 100
    )

    results.append(
        (
            ticker,
            name,
            range_low,
            range_high,
            price_range,
            range_pct
        )
    )


# --------------------------------------------------
# 3. 値幅率が大きい順に並べる
# --------------------------------------------------

results.sort(
    key=lambda x: x[5],
    reverse=True
)


# --------------------------------------------------
# 4. 結果を表示する
# --------------------------------------------------

print()
print("=== 60営業日レンジ比較 ===")
print()

print(
    f"{'Ticker':10s} "
    f"{'Name':10s} "
    f"{'Low':>10s} "
    f"{'High':>10s} "
    f"{'Range':>10s} "
    f"{'Range%':>8s}"
)

print("-" * 68)

for (
    ticker,
    name,
    range_low,
    range_high,
    price_range,
    range_pct
) in results:

    print(
        f"{ticker:10s} "
        f"{name:10s} "
        f"{range_low:10.1f} "
        f"{range_high:10.1f} "
        f"{price_range:10.1f} "
        f"{range_pct:7.1f}%"
    )