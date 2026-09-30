# StockAnalysis

日本株の株価データをPythonで分析し、「うねり取り」の候補銘柄を探すための学習用プロジェクトです。

単純に値上がりしている銘柄を探すのではなく、

- 一定期間に十分な値幅があるか
- 高値圏と安値圏を何度往復しているか
- 一方向のトレンドではなく、繰り返し上下しているか

を数値化し、多数の銘柄からチャートを確認する候補を絞り込むことを目的としています。

> このプロジェクトは株式投資・Python・データ分析の学習を目的としています。
> 売買を推奨するものではありません。

---

## 分析の基本的な考え方

指定した期間の最高値と最安値から価格レンジを求めます。

```text
Range High
    |
    | Upper Zone
    |
----------------
    |
    | 中央領域
    |
----------------
    |
    | Lower Zone
    |
Range Low
```

例えば、

```text
range_days = 60
zone_ratio = 0.25
```

の場合、

- 直近60営業日を分析
- 価格レンジ上側25%をUpper Zone
- 価格レンジ下側25%をLower Zone

として扱います。

HighがUpper Zoneへ入った場合をUPPER Touch、
LowがLower Zoneへ入った場合をLOWER Touchとして検出します。

さらに、

```text
LOWER
  ↓
UPPER
  ↓
LOWER
  ↓
UPPER
```

のように上下が切り替わった回数を `SwitchCount` として数えます。

---

## 主な評価値

### RangePct

指定期間の最安値から最高値まで、どの程度の値幅があるかを百分率で表します。

```text
RangePct = (RangeHigh - RangeLow) / RangeLow × 100
```

値幅が小さすぎる銘柄を除外するために使用します。

### SwitchCount

Upper ZoneとLower Zoneの間を何回切り替わったかを表します。

```text
LOWER → UPPER → LOWER
```

なら、

```text
SwitchCount = 2
```

です。

単純な上昇・下降ではなく、レンジ内で繰り返し上下している銘柄を探すための指標として使用します。

---

## ディレクトリ構成

```text
StockAnalysis/
│
├── 01_api_basic/
│   ├── 01_get_token.py
│   ├── 02_get_board.py
│   └── README.md
│
├── 02_historical_data/
│   ├── 01_get_history.py
│   ├── 02_plot_history.py
│   ├── ...
│   ├── 10_wave_chart.py
│   └── README.md
│
├── 03_screening/
│   ├── screening_core.py
│   ├── 01_multi_stock_range.py
│   ├── ...
│   ├── 11_large_scale_screen.py
│   ├── 12_screen_swing_trade.py
│   ├── 13_candidate_chart_sequential.py
│   └── README.md
│
├── .env
├── .gitignore
└── README.md
```

---

## 分析の流れ

現在のスクリーニングは次の流れで行います。

```text
JPX 上場銘柄一覧
        ↓
大型・中型株 約500銘柄
        ↓
11_large_scale_screen.py
        ↓
screening_core.py
        ↓
RangePct / SwitchCountを計算
        ↓
large_scale_screen_result.csv
        ↓
12_screen_swing_trade.py
        ↓
うねり候補を抽出
        ↓
swing_trade_candidates.csv
        ↓
13_candidate_chart_sequential.py
        ↓
候補チャートを1銘柄ずつ目視確認
```

機械判定だけで売買対象を決めるのではなく、

```text
機械による一次スクリーニング
        ↓
人間によるチャート確認
```

という使い方を想定しています。

---

## 使用データ

### 過去の株価

過去のOHLCデータ取得には `yfinance` を使用しています。

主に以下を利用します。

```text
Open
High
Low
Close
Volume
```

### 現在の株価

kabu Station APIを利用する実験コードを `01_api_basic` に保存しています。

### 銘柄一覧

JPXが公開している上場銘柄一覧を使用します。

`data_j.xlsx` はGit管理対象外としているため、必要に応じて取得して `03_screening` に配置します。

---

## セキュリティ

APIパスワードなどの秘密情報は `.env` に保存し、Gitには登録しません。

以下もGit管理対象外です。

```text
.env
.venv/
__pycache__/
*.pyc

03_screening/data_j.xlsx
03_screening/large_scale_screen_result.csv
03_screening/large_scale_screen_result_enriched.csv
03_screening/swing_trade_candidates.csv
```

---

## 現在のステータス

現在は、

```text
約500銘柄
 ↓
RangePct / SwitchCountによる候補抽出
 ↓
チャートによる目視確認
```

まで実装しています。

今後は、スクリーニング結果と実際のチャートを比較しながら、うねり候補の抽出条件を検証していきます。