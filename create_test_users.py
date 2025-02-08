import requests
import json
import sqlite3

BASE_URL = "http://localhost:8080"

def create_user(username, email, password, role):
    url = f"{BASE_URL}/api/users"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "role": role
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print(f"ユーザー '{username}' を作成しました。ロール: {role}")
    else:
        print(f"ユーザー '{username}' の作成に失敗しました。エラー: {response.text}")

def get_token(username, password):
    response = requests.post(
        f"{BASE_URL}/api/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"username={username}&password={password}"
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"トークンの取得に失敗しました。エラー: {response.text}")
        return None

def clear_database():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    print("データベースをクリアしました。")

if __name__ == "__main__":
    # データベースのクリア
    clear_database()

    # 管理者ユーザーの作成
    create_user("admin", "admin@example.com", "adminpassword", "admin")

    # 一般ユーザーの作成
    create_user("user", "user@example.com", "userpassword", "user")

    # ユーザーの確認
    print("\nユーザーの確認:")
    response = requests.get(f"{BASE_URL}/api/users/me", headers={"Authorization": f"Bearer {get_token('admin', 'adminpassword')}"})
    if response.status_code == 200:
        print(f"管理者ユーザー情報: {response.json()}")
    else:
        print(f"管理者ユーザーの確認に失敗しました。エラー: {response.text}")

    response = requests.get(f"{BASE_URL}/api/users/me", headers={"Authorization": f"Bearer {get_token('user', 'userpassword')}"})
    if response.status_code == 200:
        print(f"一般ユーザー情報: {response.json()}")
    else:
        print(f"一般ユーザーの確認に失敗しました。エラー: {response.text}")

print("テストユーザーの作成が完了しました。")