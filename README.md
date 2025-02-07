# All-in-One PC Setup Automation System

このプロジェクトは、PCのセットアップを自動化するための統合システムです。

## プロジェクト構成

```
root/
├── frontend/          # フロントエンドファイル
├── backend/           # バックエンドサーバー
├── scripts/           # 自動化スクリプト
└── logs/             # ログファイル
```

### コンポーネントの説明

#### フロントエンド (`frontend/`)
- HTML/CSS/JavaScriptを使用したWebインターフェース
- PCセットアップの進捗状況の可視化
- 設定項目のカスタマイズ機能

#### バックエンド (`backend/`)
- Python FastAPIを使用したRESTful API
- セットアップタスクの管理と実行
- 進捗状況の監視とログ記録

#### 自動化スクリプト (`scripts/`)
- PowerShellスクリプトによる自動化
- PSToolsとWinRMを使用したリモート操作
- システム設定の自動化と構成管理

#### ログ管理 (`logs/`)
- システムログの保存
- エラーログの記録
- 実行履歴の管理

## 技術スタック

- フロントエンド: HTML/CSS/JavaScript
- バックエンド: Python FastAPI
- 自動化: PowerShell + PSTools + WinRM
- ログ管理: カスタムログシステム

## セットアップ手順

### バックエンド開発環境のセットアップ

1. Pythonの仮想環境を作成し、有効化します:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
```

2. 必要なパッケージをインストールします:
```bash
pip install -r requirements.txt
```

3. 開発サーバーを起動します:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. APIドキュメントにアクセス:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### リモートセットアップスクリプトの使用方法

#### 前提条件
1. PSToolsのインストール
   - [PSTools](https://docs.microsoft.com/en-us/sysinternals/downloads/pstools)をダウンロード
   - システムのPATHに追加

2. WinRMの有効化
```powershell
# 管理者権限でPowerShellを開き、以下を実行
.\scripts\enable_winrm.ps1
```

#### リモートセットアップの実行
1. リモートPCのセットアップを実行:
```powershell
# 管理者権限でPowerShellを開き、以下を実行
.\scripts\remote_setup.ps1 -ComputerName "対象PC名" -Username "管理者ユーザー名" -Password (ConvertTo-SecureString -String "パスワード" -AsPlainText -Force)
```

2. 設定ファイルを使用する場合:
```powershell
.\scripts\remote_setup.ps1 -ComputerName "対象PC名" -Username "管理者ユーザー名" -Password (ConvertTo-SecureString -String "パスワード" -AsPlainText -Force) -ConfigPath "設定ファイルのパス"
```

#### ログの確認
- すべてのログは `logs/` ディレクトリに保存されます
- ログファイル名の形式: `remote_setup_YYYYMMDD_HHMMSS.log`

### 利用可能なエンドポイント

- `GET /`: APIの基本情報を取得
- `POST /setup`: PCセットアップリクエストを送信

## 貢献について

プロジェクトへの貢献は大歓迎です。Issue報告や機能提案、プルリクエストをお待ちしています。
