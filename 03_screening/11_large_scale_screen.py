"""
JPXの東証上場銘柄一覧から大型～中型株を抽出し、
screening_core.pyを使って大量銘柄のうねりを分析する。

目的:
1. JPXの data_j.xlsx を読み込む
2. TOPIX Core30 / Large70 / Mid400 を抽出する
3. JPX銘柄コードをYahoo Finance形式 xxxx.T に変換する
4. yfinanceから株価データを取得する
5. 指定した期間・Zone RatioでRange% / Switch Countを計算する
6. 全銘柄の分析結果を一覧表示する
7. Range% / Switch Countの分布を確認する
8. 分析結果をCSVへ保存する

現段階ではRange% / Switch Countによる銘柄除外は行わない。
まず大型～中型株全体の分布を確認する。
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

from screening_core import calculate_wave


# --------------------------------------------------
# 1. 分析条件
# --------------------------------------------------

RANGE_DAYS = 60
ZONE_RATIO = 0.25


# --------------------------------------------------
# 2. ファイル
#
# このPythonファイルと同じディレクトリに
# data_j.xlsx がある前提。
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

JPX_FILE = (
    SCRIPT_DIR
    / "data_j.xlsx"
)

OUTPUT_FILE = (
    SCRIPT_DIR
    / "large_scale_screen_result.csv"
)


# --------------------------------------------------
# 3. 対象とするTOPIX規模区分
# --------------------------------------------------

TARGET_GROUPS = [
    "TOPIX Core30",
    "TOPIX Large70",
    "TOPIX Mid400",
]


# --------------------------------------------------
# 4. JPX銘柄一覧を読み込む
# --------------------------------------------------

print()
print("=== JPX銘柄一覧 読み込み ===")
print()

print(
    f"File : {JPX_FILE}"
)

if not JPX_FILE.exists():

    raise FileNotFoundError(
        f"JPXファイルがありません: "
        f"{JPX_FILE}"
    )


jpx_df = pd.read_excel(
    JPX_FILE,
    dtype={
        "コード": str,
    }
)


print(
    f"JPX全銘柄数 : "
    f"{len(jpx_df)}"
)


# --------------------------------------------------
# 5. 必要な列が存在するか確認
# --------------------------------------------------

required_columns = [
    "コード",
    "銘柄名",
    "規模区分",
]

for column in required_columns:

    if column not in jpx_df.columns:

        raise ValueError(
            f"JPXファイルに"
            f"「{column}」列がありません"
        )


# --------------------------------------------------
# 6. Core30 / Large70 / Mid400を抽出
# --------------------------------------------------

target_df = (
    jpx_df[
        jpx_df["規模区分"].isin(
            TARGET_GROUPS
        )
    ]
    .copy()
)


# --------------------------------------------------
# 7. 銘柄コードを整形
#
# 4507
#   ↓
# 4507.T
# --------------------------------------------------

target_df["コード"] = (
    target_df["コード"]
    .astype(str)
    .str.strip()
)


target_df["Ticker"] = (
    target_df["コード"]
    + ".T"
)


# --------------------------------------------------
# 8. 重複を除去
# --------------------------------------------------

target_df = (
    target_df
    .drop_duplicates(
        subset=["Ticker"]
    )
    .reset_index(drop=True)
)


print()

print(
    f"分析対象銘柄数 : "
    f"{len(target_df)}"
)

print()

print("規模区分内訳:")

group_counts = (
    target_df["規模区分"]
    .value_counts()
)

for group in TARGET_GROUPS:

    count = int(
        group_counts.get(
            group,
            0
        )
    )

    print(
        f"  {group:15s} : "
        f"{count:4d}"
    )


# --------------------------------------------------
# 9. 全銘柄を分析
# --------------------------------------------------

print()
print("=== うねり分析開始 ===")
print()

results = []

error_count = 0

total_count = len(
    target_df
)


for index, row in target_df.iterrows():

    ticker = row["Ticker"]
    code = row["コード"]
    name = row["銘柄名"]
    group = row["規模区分"]

    current_number = (
        index + 1
    )


    print(
        f"[{current_number:3d}/"
        f"{total_count:3d}] "
        f"{ticker:8s} "
        f"{name}"
    )


    try:

        # --------------------------------------------------
        # 株価取得
        #
        # 100日以上あれば今回の60日分析には十分だが、
        # 余裕を持って1年取得する。
        # --------------------------------------------------

        stock = yf.Ticker(
            ticker
        )

        df = stock.history(
            period="1y",
            auto_adjust=False
        )


        # --------------------------------------------------
        # データなし
        # --------------------------------------------------

        if df.empty:

            raise ValueError(
                "株価データなし"
            )


        # --------------------------------------------------
        # screening_coreで分析
        # --------------------------------------------------

        result = calculate_wave(
            df,
            range_days=RANGE_DAYS,
            zone_ratio=ZONE_RATIO
        )


        # --------------------------------------------------
        # 結果保存
        # --------------------------------------------------

        results.append(
            {
                "Code":
                    code,

                "Ticker":
                    ticker,

                "Name":
                    name,

                "Group":
                    group,

                "RangeDays":
                    RANGE_DAYS,

                "ZoneRatio":
                    ZONE_RATIO,

                "RangeLow":
                    result[
                        "range_low"
                    ],

                "RangeHigh":
                    result[
                        "range_high"
                    ],

                "RangePct":
                    result[
                        "range_pct"
                    ],

                "TouchCount":
                    result[
                        "touch_count"
                    ],

                "AlternatingTouchCount":
                    result[
                        "alternating_touch_count"
                    ],

                "SwitchCount":
                    result[
                        "switch_count"
                    ],
            }
        )


    except Exception as error:

        error_count += 1

        print(
            f"    ERROR: {error}"
        )


# --------------------------------------------------
# 10. DataFrameへ変換
# --------------------------------------------------

result_df = pd.DataFrame(
    results
)


if result_df.empty:

    raise RuntimeError(
        "分析できた銘柄がありません"
    )


# --------------------------------------------------
# 11. Switch → Range% の順で並べ替え
# --------------------------------------------------

result_df = (
    result_df
    .sort_values(
        by=[
            "SwitchCount",
            "RangePct",
        ],
        ascending=[
            False,
            False,
        ]
    )
    .reset_index(drop=True)
)


# --------------------------------------------------
# 12. 分析結果表示
# --------------------------------------------------

print()
print(
    "=== Large Scale Screening Result ==="
)
print()

print(
    f"RANGE_DAYS = "
    f"{RANGE_DAYS}"
)

print(
    f"ZONE_RATIO = "
    f"{ZONE_RATIO:.2f}"
)

print()

print(
    f"成功 : "
    f"{len(result_df)} 銘柄"
)

print(
    f"失敗 : "
    f"{error_count} 銘柄"
)

print()


# --------------------------------------------------
# 13. 上位30銘柄を表示
#
# まだ「候補30銘柄」ではない。
# Switch / Range%順に並べた観察用。
# --------------------------------------------------

print(
    "=== Switch / Range% 上位30銘柄 ==="
)
print()

print(
    f"{'Ticker':9s} "
    f"{'Name':18s} "
    f"{'Range%':>8s} "
    f"{'Switch':>7s}"
)

print("-" * 50)


for _, row in result_df.head(30).iterrows():

    print(
        f"{row['Ticker']:9s} "
        f"{row['Name'][:18]:18s} "
        f"{row['RangePct']:7.1f}% "
        f"{int(row['SwitchCount']):7d}"
    )


# --------------------------------------------------
# 14. Switch Count分布
# --------------------------------------------------

print()
print(
    "=== Switch Count 分布 ==="
)
print()

switch_distribution = (
    result_df[
        "SwitchCount"
    ]
    .value_counts()
    .sort_index()
)


for switch_count, count in (
    switch_distribution.items()
):

    print(
        f"Switch {int(switch_count):2d} : "
        f"{int(count):4d} 銘柄"
    )


# --------------------------------------------------
# 15. Range%分布
#
# 0～5%
# 5～10%
# 10～15%
# ...
# --------------------------------------------------

print()
print(
    "=== Range% 分布 ==="
)
print()


range_bins = [
    0,
    5,
    10,
    15,
    20,
    25,
    30,
    40,
    50,
    1000,
]

range_labels = [
    " 0 -  5%",
    " 5 - 10%",
    "10 - 15%",
    "15 - 20%",
    "20 - 25%",
    "25 - 30%",
    "30 - 40%",
    "40 - 50%",
    "50%以上",
]


range_categories = pd.cut(
    result_df["RangePct"],
    bins=range_bins,
    labels=range_labels,
    right=False
)


range_distribution = (
    range_categories
    .value_counts()
    .sort_index()
)


for range_name, count in (
    range_distribution.items()
):

    print(
        f"{range_name:10s} : "
        f"{int(count):4d} 銘柄"
    )


# --------------------------------------------------
# 16. 参考:
# Range >= 10% かつ Switch >= 3
#
# まだ正式なPASS条件ではない。
# 候補数を確認するためだけに表示する。
# --------------------------------------------------

reference_df = (
    result_df[
        (
            result_df["RangePct"]
            >= 10.0
        )
        &
        (
            result_df["SwitchCount"]
            >= 3
        )
    ]
    .copy()
)


print()
print(
    "=== 参考条件 ==="
)
print()

print(
    "Range% >= 10.0"
)

print(
    "Switch >= 3"
)

print()

print(
    f"該当銘柄数 : "
    f"{len(reference_df)} / "
    f"{len(result_df)}"
)


# --------------------------------------------------
# 17. CSV保存
# --------------------------------------------------

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


print()
print(
    "=== CSV保存 ==="
)
print()

print(
    OUTPUT_FILE
)

print()
print(
    "分析完了"
)