# 01_api_basic

kabu Station APIの基本的な使い方を確認するためのサンプルです。

## 目的

Pythonからkabu Station APIへアクセスし、

```text
Python
  ↓
kabu Station API
  ↓
トークン取得
  ↓
現在の株価情報取得
```

という基本的な通信を確認します。

---

## ファイル

### 01_get_token.py

kabu Station APIへ接続するためのトークンを取得します。

APIパスワードはソースコードへ直接記述せず、`.env` から取得する構成を想定しています。

### 02_get_board.py

取得したトークンを使用して、指定銘柄の板・現在値などの情報を取得します。

---

## 注意

kabu Station APIは主に現在の市場情報を取得するために使用しています。

本プロジェクトで必要となる数十～数百営業日の過去株価分析については、`02_historical_data` および `03_screening` で `yfinance` を使用しています。

APIパスワードやトークンなどの秘密情報はGitへ登録しません。