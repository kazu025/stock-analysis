"""
kabuステーションAPIに接続し、APIトークンを取得する。

処理の流れ:
1. APIパスワードを入力する
2. kabuステーションの /token APIへPOSTする
3. 返されたトークンを表示する
"""

import getpass
import requests


# kabuステーションAPIのトークン発行URL
URL = "http://localhost:18080/kabusapi/token"

# APIパスワードを画面から入力
# getpass()を使うと、入力した文字は画面に表示されない
api_password = getpass.getpass("APIパスワード: ")

# kabuステーションへ送信するデータ
data = {
    "APIPassword": api_password
}

# JSON形式でPOSTする
response = requests.post(URL, json=data)

# HTTPステータスコードを表示
print(f"HTTP Status : {response.status_code}")

# kabuステーションから返されたJSONを取得
result = response.json()

# 結果を表示
print(result)