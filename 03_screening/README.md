# 03_screening

複数の日本株を対象に「うねり」を測定し、大型・中型株の中から候補銘柄を抽出するためのスクリーニングコードです。

## 基本方針

スクリーニングを、

```text
測定
 ↓
候補抽出
 ↓
チャート確認
```

の3段階に分けています。

---

## screening_core.py

うねりを測定する共通モジュールです。

```python
calculate_wave(
    df,
    range_days,
    zone_ratio
)
```

を呼び出すことで、指定期間の株価からうねりを測定します。

例えば、

```python
result = calculate_wave(
    df,
    range_days=60,
    zone_ratio=0.25
)
```

とすると、

```text
直近60営業日
上下それぞれ25%をZone
```

として分析します。

主な出力は、

```text
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
```

です。

重要なのは、

```text
RangePct
SwitchCount
```

です。

`screening_core.py` 自体は銘柄をPASS / FAIL判定しません。

あくまで「測定」を担当し、候補選別は別のプログラムで行います。

---

## 初期検証

### 01_multi_stock_range.py

複数銘柄についてRangePctを比較します。

RangePctだけでは、一方向に上昇・下降している銘柄も高評価になることを確認しました。

### 02_multi_stock_touch.py

複数銘柄についてTouch / Switchを比較します。

### 03_multi_stock_ma.py

MA25 / MA75の傾きを比較します。

移動平均だけではうねりを適切に評価できないため、補助指標として扱います。

### 04_screen_candidates.py

RangePct、SwitchCount、移動平均などを使った初期スクリーニングを試します。

### 05_candidate_chart.py

1銘柄の候補チャートを表示します。

### 06_compare_charts.py

複数銘柄のチャートを並べて比較します。

---

## パラメータ検証

### 07_zone_sensitivity.py

`zone_ratio` を変更してSwitchCountがどの程度変化するかを調べます。

例：

```text
0.20
0.25
0.30
```

### 08_range_days_sensitivity.py

分析期間を変更して結果を比較します。

例：

```text
40日
60日
80日
100日
```

### 09_multi_period_screen.py

複数期間のSwitchCountを同時に比較します。

単一期間だけでは見えにくい、

```text
最近だけうねっている
長期間安定してうねっている
```

といった違いを確認します。

---

## 共通処理の確認

### 10_test_screening_core.py

`screening_core.py` の計算結果が、それ以前の検証コードと一致することを確認します。

これにより、個別に実装していたRange / Zone / Touch / Switch計算を共通化しました。

---

## 大規模スクリーニング

### 11_large_scale_screen.py

JPXの上場銘柄一覧から大型・中型株を対象として、約500銘柄を分析します。

各銘柄について `screening_core.py` を使用し、

```text
RangePct
SwitchCount
```

などを計算します。

結果は、

```text
large_scale_screen_result.csv
```

へ保存します。
## スクリーニング結果の補強

### enrich_screening_results.py

`11_large_scale_screen.py` が作成した、

```text
large_scale_screen_result.csv
```

に、現在の株価位置や最後のSwitchからの経過日数を追加します。

追加する主な情報は、

```text
LastSwitchDate
CurrentPrice
CurrentPositionPct
DaysSinceLastSwitch
```

です。

`CurrentPositionPct` は、現在株価が60日Rangeのどの位置にあるかを0～100%で表します。

```text
Range High   100%
      |
      |  ← CurrentPrice
      |
Range Low      0%
```

これにより、過去にうねりが多かったかだけでなく、

- 最後のSwitchが最近発生したか
- 現在株価がRangeのどこに位置しているか

も候補抽出時に利用できます。

結果は、

```text
large_scale_screen_result_enriched.csv
```

へ保存します。

---

## 候補抽出

### 12_screen_swing_trade.py

`large_scale_screen_result.csv` から、うねり取りの候補を抽出します。

現在の初期条件は、

```python
MIN_RANGE_PCT = 10.0
MIN_SWITCH_COUNT = 4
```

です。

つまり、

```text
RangePct >= 10%
SwitchCount >= 4
```

を基本条件としています。

条件を通過した銘柄は、

```text
swing_trade_candidates.csv
```

へ保存します。

この条件は最終的な売買判定ではなく、約500銘柄から人間が確認できる数まで候補を減らすための一次スクリーニングです。

---

## 候補チャート確認

### 13_candidate_chart_sequential.py

`swing_trade_candidates.csv` に保存された候補を1銘柄ずつチャート表示します。

表示内容は、

```text
Close
MA25
MA75
Range High
Range Low
Upper Zone
Lower Zone
UPPER / LOWER Touch
RangePct
SwitchCount
```

です。

チャートウィンドウを閉じると、次の候補銘柄を表示します。

これにより、

```text
機械判定ではうねっている
        ↓
実際のチャートでも綺麗に往復しているか？
```

を人間が確認します。

---

## 現在のスクリーニングフロー

```text
data_j.xlsx
      ↓
大型・中型株 約500銘柄
      ↓
11_large_scale_screen.py
      ↓
screening_core.calculate_wave()
      ↓
large_scale_screen_result.csv
      ↓
enrich_screening_results.py
      ↓
large_scale_screen_result_enriched.csv
      ↓
12_screen_swing_trade.py
      ↓
swing_trade_candidates.csv
      ↓
13_candidate_chart_sequential.py
      ↓
チャート目視確認
```

---

## 現在使用している主なパラメータ

```text
Range Days : 60営業日
Zone Ratio : 0.25
Min Range  : 10%
Min Switch : 4
```

これらは固定された最適値ではありません。

実際のチャートとスクリーニング結果を比較しながら、条件の妥当性を検証していきます。

---

## 注意点

現在のアルゴリズムでは、日足のHigh / Lowを使用してZoneへの到達を判定しています。

そのため、同一営業日にUpper ZoneとLower Zoneの両方へ到達するような大きな値動きがあった場合、日足OHLCだけでは「どちらへ先に到達したか」を判定できません。

今後、大規模スクリーニング結果を検証する際の改善候補とします。

また、スクリーニング結果は売買を保証するものではありません。

最終的にはチャート、企業業績、決算、ニュースなども確認することを想定しています。