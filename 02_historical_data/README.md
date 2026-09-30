# 02_historical_data

過去の株価データを使い、「うねり」をどのように数値化するかを段階的に検証した学習用コードです。

## 目的

最初からスクリーニングプログラムを作るのではなく、1銘柄の株価を使って、

```text
値幅
 ↓
移動平均
 ↓
Upper / Lower Zone
 ↓
Touch
 ↓
上下の切り替わり
 ↓
うねり周期
```

と順番に分析方法を確認しています。

主な検証銘柄として塩野義製薬（4507）などを使用しました。

---

## ファイル

### 01_get_history.py

`yfinance` から過去の株価を取得します。

高値・安値・終値など、後続の分析で使用する基本データを確認します。

### 02_plot_history.py

過去株価をチャート表示します。

Close、MA25、MA75、期間高値・安値などを表示し、数値だけではなくチャートでも状態を確認します。

### 03_ma_slope.py

MA25、MA75の変化率を調べます。

移動平均線が大きく上昇・下降しているのか、それとも比較的横ばいなのかを確認するための実験です。

### 04_range_analysis.py

20日、40日、60日、100日、250日など複数期間の値幅を比較します。

これにより、うねりを見る期間として何日程度が適切かを検討しました。

### 05_range_touch.py

価格レンジの上下にZoneを設定し、そのZoneへ株価が到達した日数を調べます。

### 06_touch_count.py

Zone内に滞在した日数ではなく、

```text
Zone外 → Zone内
```

となった瞬間をTouchとして検出します。

GPIOの立ち上がりエッジ検出に近い考え方です。

### 07_touch_price_compare.py

CloseだけでZone判定する方法と、High / Lowを使用する方法を比較します。

現在の分析では、

```text
Upper : High
Lower : Low
```

を使用しています。

### 08_alternating_touch.py

同じ側への連続Touchをまとめ、

```text
LOWER
LOWER
UPPER
UPPER
LOWER
```

を、

```text
LOWER
UPPER
LOWER
```

として扱います。

これによって、上下方向の切り替わりを数えられるようにしました。

### 09_wave_period.py

LOWER → UPPER、UPPER → LOWERなどの間隔を営業日数で調べます。

### 10_wave_chart.py

Range、Upper / Lower Zone、Touch位置などをチャート上に表示し、計算結果と実際の株価の動きを比較します。

---

## このディレクトリで得られた考え方

単純に、

```text
値幅が大きい銘柄
```

を探すだけでは、うねり取り候補にはなりません。

例えば、

```text
安値 → 急上昇 → 高値
```

という一方向の動きでもRangePctは大きくなります。

そこで、

```text
RangePct
+
Upper / LowerのSwitchCount
```

を組み合わせて評価する方法へ進みました。

この検証結果を共通処理としてまとめたものが、

```text
03_screening/screening_core.py
```

です。