# GUIの起動と操作

```powershell
Set-Location F:\009-StockAnalysis
& .\.venv\Scripts\python.exe .\06_jpx_universe\jpx_gui.py
```

PySide6が未導入の環境では先に以下を実行する。

```powershell
& .\.venv\Scripts\python.exe -m pip install -r .\06_jpx_universe\requirements-gui.txt
```

1. 「保存済みExcelを読む」を押す。初回取得や更新は「JPXから最新データを取得」。
2. 17業種・33業種・規模区分・市場のチェックを選ぶ。同じ一覧内はOR、一覧間はAND。未選択は制限なし。
3. 必要なら追加CSVを参照する（1ファイル）。手入力CSVの仕様は既存README参照。
4. 「対象銘柄を表示」で内容と件数を確認する。
5. 保存先を指定して「CSVを保存」。既存CSVへの保存時は上書きを確認する。

保存時は現在の条件で再計算する。取得や読込だけでは既存CSVを変更しない。
0件・不正入力では保存しない。原本保存・履歴・重複排除はjpx_universe.pyの既存処理を共用。
ダウンロード中は操作を無効にし、完了後に再度操作できる。

Designerのjpx_universe.uiを起動時に直接読み込む。部品名は変更しない。
保存された.uiにレイアウトがない場合は、起動時に部品を伸縮可能な配置へ並べ直す。
保存先参照ボタンがない場合も起動時に補う。.ui自体は書き換えない。
定期実行は既存update_jpx.ps1とタスクスケジューラを使用する。
