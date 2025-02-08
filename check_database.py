import sqlite3
from pathlib import Path

# データベースファイルのパスを設定
db_path = Path(__file__).parent / "data.db"

# データベースに接続
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# ユーザーテーブルの内容を取得
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print("ユーザーテーブルの内容:")
for user in users:
    print(user)

# 接続を閉じる
conn.close()