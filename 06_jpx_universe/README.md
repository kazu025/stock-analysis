# JPX公式Excelから銘柄CSVを作る

このフォルダーは `F:\009-StockAnalysis\06_jpx_universe` に配置する。
Python 3.10以上を使用。既存のチャート・分析処理は変更しない。

## 1. 準備と原本取得

```powershell
Set-Location F:\009-StockAnalysis
& .\.venv\Scripts\python.exe -m pip install -r .\06_jpx_universe\requirements.txt
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_universe.py --download-only
```

取得元: [JPX 東証上場銘柄一覧](https://www.jpx.co.jp/markets/statistics-equities/misc/01.html)

2026-10-18に実ファイルを確認。掲載分は2026年9月末、4,447行。
現時点のダウンロードURLは
`https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx`。
プログラムは毎回公式一覧ページのリンクを探すため、添付ディレクトリの変更にも対応する。
リンク消失・複数候補・列変更はエラーにし、自動で非公式データへ切り替えない。

実際の列:
`日付 / コード / 銘柄名 / 市場・商品区分 / 33業種コード / 33業種区分 / 17業種コード / 17業種区分 / 規模コード / 規模区分`。

原本を加工せず `data\jpx\data_j.xlsx` に保存する。
`data\jpx\history\data_j_<基準日>_<SHA256>.xlsx` にも保存し、
同名JSONに取得URL・確認時刻・ハッシュ・件数を記録する。同一内容のExcelは重複保存しない。

## 2. 指定できる区分を確認

```powershell
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_universe.py --offline --list-values
```

業種・規模・市場の**正式名称を完全一致**で指定する。
規模は現在 `TOPIX Core30` / `TOPIX Large70` / `TOPIX Mid400` /
`TOPIX Small 1` / `TOPIX Small 2` / `-`。
`-` は規模区分が付与されていない行であり、Smallの意味ではない。
全件はETF等も含む。内国普通株式に限定する場合は `--market` を指定する。
原本には種類株式など5桁コードが7件含まれる。原本はそのまま保存し、これらは
Yahoo Financeの4桁.T形式に機械変換せずCSV対象から除外して件数を表示する。
規模区分だけで最新のTOPIX構成銘柄を断定しない。必要なら公式の構成銘柄一覧を確認する。

## 3. 条件を絞りCSVを生成

大型・中型株をまとめる（同じ項目の複数指定はOR）:

```powershell
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_universe.py `
  --size 'TOPIX Core30' --size 'TOPIX Large70' --size 'TOPIX Mid400'
```

17業種と33業種を指定（異なる項目間はAND）:

```powershell
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_universe.py --offline `
  --sector17 '自動車・輸送機' --sector33 '輸送用機器' `
  --market 'プライム（内国株式）' `
  --output .\data\jpx\transport.csv
```

条件省略は全件。`--offline` は保存済み原本を明示的に使う指定。
通常は必ずネット取得し、通信失敗時に古い原本へ黙って切り替えない。
存在しない条件名・0件結果はエラーにして既存CSVを保持する。

## 4. 手入力CSVの銘柄を追加

```powershell
Copy-Item .\06_jpx_universe\manual.example.csv .\data\jpx\manual.csv
notepad .\data\jpx\manual.csv
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_universe.py --offline `
  --size 'TOPIX Core30' --manual .\data\jpx\manual.csv
```

CSVはUTF-8（BOMあり/なし）。`Ticker` または `Code` が必要。
`7203`・`7203.T`・英字入りコードを受け付け、大文字の `.T` 形式に統一する。
`Name` と `Group` は省略でき、JPX掲載銘柄は原本から補完する。
JPXにない銘柄はName必須、Group省略時はManual。上場・株価取得の可否は保証しない。
TickerとCodeを両方書く場合は一致が必要。空のコードや不正行は出力前にエラーとする。

手入力銘柄はフィルターに関係なく最後に追加する。
重複は正規化したTickerで排除し、「JPX抽出結果→手入力ファイルの指定順→行順」の先勝ち。
既に抽出された銘柄のName/Groupを手入力で上書きしない。
`--manual` を繰り返すと複数ファイルを追加できる。

## 5. 既存チャートで表示

既定出力は `data\jpx\universe.csv`。
列は `Ticker,Name,Group,Code,Sector17,Sector33,Market`。
Nameは銘柄名、GroupはJPX規模区分。UTF-8 BOM付きで、Ticker順ではなく原本順を保持する。

既存 `03_screening\13_candidate_chart_sequential.py` は `CSV_FILE` を読み込むので、
その1行を次に変更すれば生成CSVを直接表示できる:

```python
CSV_FILE = SCRIPT_DIR.parent / 'data' / 'jpx' / 'universe.csv'
```

既存ファイルを編集せず動作を確認する方法:

```powershell
& .\.venv\Scripts\python.exe -c "import importlib.util,pathlib; p=pathlib.Path('03_screening/13_candidate_chart_sequential.py'); s=importlib.util.spec_from_file_location('chart',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.CSV_FILE=pathlib.Path('data/jpx/universe.csv'); m.main()"
```

これは区分による銘柄リストであり、Range/Switchによる候補抽出結果ではない。
既存の `swing_trade_candidates.csv` は自動で上書きしない。

## 6. 定期取得（Windowsタスクスケジューラ）

JPXは毎月第3営業日の午前9時以降に前月末分を掲載するため、
月初の休日や公開遅れにも対応できるよう毎日09:30の確認例とする。
以下はWindowsのタイムゾーンが日本時間の場合。登録は利用者が必要なときに実行する。
初期設定ではタスクを自動登録しない。

まず手動実行（Core30/Large70/Mid400、ログ保存、失敗時は終了コード1）:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File F:\009-StockAnalysis\06_jpx_universe\update_jpx.ps1
```

条件・手入力を毎回使う場合は `update_jpx.ps1` のPython呼び出し行へ引数を追加する。
パスは絶対パスにする。ログは `data\jpx\logs\yyyy-MM-dd.log`。

```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "F:\009-StockAnalysis\06_jpx_universe\update_jpx.ps1"' `
  -WorkingDirectory 'F:\009-StockAnalysis'
$trigger = New-ScheduledTaskTrigger -Daily -At '09:30'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'StockAnalysis-JPX-Universe' `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description 'JPX原本を保存し大型・中型株CSVを更新する'
Get-ScheduledTaskInfo -TaskName 'StockAnalysis-JPX-Universe'
# 停止が必要なとき:
# Unregister-ScheduledTask -TaskName 'StockAnalysis-JPX-Universe' -Confirm:$false
```

この例は現在のユーザーのログオン中に実行する。未ログオン時にも実行したい場合は
タスクスケジューラのセキュリティ設定で利用環境に合わせて設定する。
別セッションでもFドライブが見えることを確認する。

## 7. 保護と検証

取得データをメモリ上でExcelとして開き、必須列・コード・日付・重複等を検証してから
原本と履歴を保存する。取得または原本検証の失敗は既存原本・CSVを変更しない。
手入力・条件の不備では取得済み原本が更新されることはあるが、既存CSVは保持する。
ファイルごとに同じディレクトリの一時ファイルへ書き、完成後に置換する。
複数ファイル全体のトランザクションではない。Excel等が出力を開いて置換できない場合もエラーになる。
手動実行とタスクを同時に走らせない。

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s .\06_jpx_universe -p 'test_*.py' -v
```

取得失敗、壊れた応答、原本履歴、業種/規模フィルター、英字コード、手入力重複、
5桁コードを原本に保持してCSV対象から除外する処理、
不正入力、0件時の既存CSV保護、既存チャートと同じ読み込み方法を検証する。
`data/` は既存のGit除外設定の対象。手入力ファイルのバックアップは別途保持する。
