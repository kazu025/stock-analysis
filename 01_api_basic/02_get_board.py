"""
kabuステーションAPIから指定銘柄の時価情報・板情報を取得する。

処理の流れ:
1. APIパスワードを入力する
2. /token APIへPOSTしてトークンを取得する
3. トークンをX-API-KEYヘッダーに設定する
4. /board APIへGETする
5. キヤノン（7751）の時価情報を表示する
"""

import getpass
import requests
import pprint


# kabuステーションAPI
BASE_URL = "http://localhost:18080/kabusapi"

# キヤノン（7751）、市場コード1 = 東証
SYMBOL = "7751@1"


# --------------------------------------------------
# 1. APIトークン取得
# --------------------------------------------------

api_password = getpass.getpass("APIパスワード: ")

token_url = f"{BASE_URL}/token"

data = {
    "APIPassword": api_password
}

response = requests.post(token_url, json=data)

print(f"Token HTTP Status : {response.status_code}")

response.raise_for_status()

token_result = response.json()

token = token_result["Token"]

print("Token取得成功")


# --------------------------------------------------
# 2. キヤノンの時価情報・板情報取得
# --------------------------------------------------
# 時価情報・板情報
board_url = f"{BASE_URL}/board/{SYMBOL}"
# HTTPリクエストのヘッダーに取得したTokenをつける
headers = {
    "X-API-KEY": token
}

response = requests.get(board_url, headers=headers)

print(f"Board HTTP Status : {response.status_code}")

response.raise_for_status()

board = response.json()


# --------------------------------------------------
# 3. 取得した情報を表示
# --------------------------------------------------

print()
print("=== 銘柄情報 ===")
print(f"銘柄コード : {board.get('Symbol')}")
print(f"銘柄名     : {board.get('SymbolName')}")
print(f"現在値     : {board.get('CurrentPrice')}")
print(f"前日終値   : {board.get('PreviousClose')}")
print(f"始値       : {board.get('OpeningPrice')}")
print(f"高値       : {board.get('HighPrice')}")
print(f"安値       : {board.get('LowPrice')}")

# --------------------------------------------------
# 4. Json全体 
# --------------------------------------------------
pprint.pprint(board)

