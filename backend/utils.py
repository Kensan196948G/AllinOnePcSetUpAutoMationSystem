import csv
from io import StringIO
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from pathlib import Path
import asyncio
import subprocess
import json
import os
from uuid import uuid4

from .models import ComputerInfo, LoginType, SetupRequest, SetupOptions

# ログディレクトリの設定
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOGS_DIR.mkdir(exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOGS_DIR / "backend.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_request_id() -> str:
    """一意のリクエストIDを生成"""
    return str(uuid4())

async def execute_powershell_script(
    script_path: str,
    computer_name: str,
    username: str,
    password: str,
    args: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    PowerShellスクリプトを実行する

    Args:
        script_path (str): 実行するスクリプトのパス
        computer_name (str): 対象コンピュータ名
        username (str): 実行ユーザー名
        password (str): パスワード
        args (Optional[Dict[str, Any]]): スクリプトに渡す追加の引数

    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: 
            - 成功したかどうか
            - メッセージ
            - スクリプトの出力(JSON形式の場合)
    """
    try:
        # スクリプトの存在確認
        script_path = str(SCRIPTS_DIR / script_path)
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"スクリプトが見つかりません: {script_path}")

        # コマンドの構築
        cmd = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-ComputerName", computer_name,
            "-Username", username,
            "-Password", password
        ]

        # 追加の引数を追加
        if args:
            for key, value in args.items():
                cmd.extend([f"-{key}", str(value)])

        # スクリプトの実行
        logger.info(f"PowerShellスクリプトを実行: {script_path}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 出力の取得
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode('utf-8', errors='replace')
        stderr_str = stderr.decode('utf-8', errors='replace')

        # 実行結果のログ記録
        log_file = LOGS_DIR / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== STDOUT ===\n{stdout_str}\n\n=== STDERR ===\n{stderr_str}")

        # エラーチェック
        if process.returncode != 0:
            error_msg = f"スクリプト実行エラー: {stderr_str}"
            logger.error(error_msg)
            return False, error_msg, None

        # JSON出力の解析を試みる
        try:
            result_data = json.loads(stdout_str)
            return True, "スクリプトが正常に実行されました", result_data
        except json.JSONDecodeError:
            # JSON形式でない場合は標準出力をそのまま返す
            return True, stdout_str, None

    except Exception as e:
        error_msg = f"スクリプト実行中に例外が発生: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

async def execute_setup_task(
    task_name: str,
    computer_info: ComputerInfo,
    setup_options: Dict[str, Any]
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    セットアップタスクを実行する

    Args:
        task_name (str): 実行するタスク名
        computer_info (ComputerInfo): コンピュータ情報
        setup_options (Dict[str, Any]): セットアップオプション

    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: 実行結果
    """
    # タスクとスクリプトのマッピング
    task_scripts = {
        "setup_desktop_icons": "setup_desktop.ps1",
        "move_vpn_icon": "move_vpn_icon.ps1",
        "install_office": "install_office.ps1",
        "setup_office_auth": "setup_office_auth.ps1",
        "install_carbon_black": "install_carbon_black.ps1",
        "install_forticlient_vpn": "install_forticlient.ps1",
        "update_windows": "update_windows.ps1",
        "cleanup_system": "cleanup_system.ps1"
    }

    # タスクに対応するスクリプトの取得
    script_name = task_scripts.get(task_name)
    if not script_name:
        return False, f"タスク '{task_name}' に対応するスクリプトが定義されていません", None

    # ログイン情報の取得
    username, password = get_login_credentials(computer_info)
    if not username or not password:
        return False, "ログイン情報が不足しています", None

    # スクリプトの実行
    success, message, result = await execute_powershell_script(
        script_name,
        computer_info.computer_name,
        username,
        password,
        setup_options
    )

    return success, message, result

def get_login_credentials(computer_info: ComputerInfo) -> Tuple[Optional[str], Optional[str]]:
    """ログイン情報を取得"""
    if computer_info.login_type == LoginType.AD:
        return computer_info.ad_username, computer_info.ad_password
    elif computer_info.login_type == LoginType.LOCAL_EXISTING:
        return computer_info.local_existing_username, computer_info.local_existing_password
    elif computer_info.login_type == LoginType.LOCAL_NEW:
        return computer_info.local_new_username, computer_info.local_new_password
    return None, None

def parse_csv_data(csv_content: str) -> List[ComputerInfo]:
    """CSVファイルの内容をパースしてComputerInfoオブジェクトのリストを返す"""
    try:
        # CSVの行を分割
        lines = csv_content.splitlines()
        
        # 10行目以降のデータを取得
        if len(lines) < 10:
            raise ValueError("CSVファイルのデータが不足しています")
        
        # ヘッダー行を取得(5行目)
        header_line = lines[4].strip()
        if not header_line:
            raise ValueError("ヘッダー行が空です")
        
        headers = []
        current_header = ""
        in_quotes = False
        
        # ヘッダーを適切に分割(カンマを含むヘッダーに対応)
        for char in header_line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                if current_header.strip():
                    headers.append(current_header.strip())
                current_header = ""
            else:
                current_header += char
        
        if current_header.strip():
            headers.append(current_header.strip())
        
        # 空のヘッダーを除外
        headers = [h.strip('"') for h in headers if h.strip()]
        
        # データ行の処理
        data_lines = [line for line in lines[9:] if line.strip()]
        if not data_lines:
            raise ValueError("データが見つかりません")
        
        # DictReaderでパース
        reader = csv.DictReader(StringIO('\n'.join(data_lines)), fieldnames=headers)
        
        # ヘッダーとデータの内容をログに出力
        logger.info(f"ヘッダー: {headers}")
        logger.info(f"データ行数: {len(data_lines)}")

        # ヘッダーとログイン種別の対応を確認
        login_type_header = next((h for h in headers if h in ['ログイン種別', 'login_type', 'ログインタイプ']), None)
        if not login_type_header:
            raise ValueError("ヘッダーに'ログイン種別'、'login_type'、または'ログインタイプ'が見つかりません")
        logger.info(f"ログインタイプヘッダー: {login_type_header}")
        computers = []
        
        for row in reader:
            # LoginTypeの検証と変換
            login_type_map = {
                'AD': LoginType.AD,
                'ActiveDirectory': LoginType.AD,
                '既存ローカル': LoginType.LOCAL_EXISTING,
                'LocalExisting': LoginType.LOCAL_EXISTING,
                '新規ローカル': LoginType.LOCAL_NEW,
                'LocalNew': LoginType.LOCAL_NEW
            }
            
            login_type_value = row.get(login_type_header, '').strip()
            login_type = login_type_map.get(login_type_value)
            if not login_type:
                logger.error(f"不正なログインタイプです: {login_type_value}")
                logger.error(f"行の内容: {row}")
                logger.error(f"利用可能なキー: {row.keys()}")
                raise ValueError(f"不正なログインタイプです: {login_type_value}\n有効な値: AD, 既存ローカル, 新規ローカル")
            logger.info(f"ログインタイプ: {login_type_value} -> {login_type}")
            
            # ComputerInfoオブジェクトの作成
            computer = ComputerInfo(
                computer_name=row.get('computer_name') or row.get('ホスト名'),
                ip_address=row.get('ip_address') or row.get('IPアドレス'),
                login_type=login_type,
                ad_username=row.get('ad_username') or row.get('ADユーザ'),
                ad_password=row.get('ad_password') or row.get('ADパスワード'),
                local_existing_username=row.get('local_existing_username') or row.get('既存ローカルユーザ'),
                local_existing_password=row.get('local_existing_password') or row.get('既存ローカルユーザパスワード'),
                full_name=row.get('full_name') or row.get('フルネーム'),
                local_new_username=row.get('local_new_username') or row.get('新規ローカルユーザー名'),
                local_new_password=row.get('local_new_password') or row.get('新規ローカルユーザーパスワード'),
                admin_privilege=(row.get('admin_privilege') or row.get('Administrator権限', '')).lower() == 'yes'
            )
            computers.append(computer)
        
        return computers
    
    except Exception as e:
        logger.error(f"CSVパースエラー: {str(e)}")
        raise

def create_setup_request(
    requester: str,
    computers: List[ComputerInfo],
    setup_options: Dict[str, bool]
) -> SetupRequest:
    """セットアップリクエストを作成する"""
    try:
        # SetupOptionsの作成
        options = SetupOptions(**setup_options)
        
        # SetupRequestの作成
        request = SetupRequest(
            requester=requester,
            computers=computers,
            setup_options=options,
            current_progress={comp.computer_name: 0.0 for comp in computers}
        )
        
        logger.info(f"セットアップリクエストを作成: {request.request_id}")
        return request
    
    except Exception as e:
        logger.error(f"セットアップリクエスト作成エラー: {str(e)}")
        raise

def validate_setup_request(request: SetupRequest) -> bool:
    """セットアップリクエストのバリデーションを行う"""
    try:
        # コンピュータ情報の検証
        for computer in request.computers:
            # ADアカウントの場合はパスワード不要
            if computer.login_type == LoginType.AD and computer.password:
                logger.warning(f"ADアカウントにパスワードが指定されています: {computer.computer_name}")
            
            # ローカルアカウントの場合はパスワード必須
            if computer.login_type != LoginType.AD and not computer.password:
                raise ValueError(f"ローカルアカウントにパスワードが指定されていません: {computer.computer_name}")
        
        # 少なくとも1つのセットアップオプションが選択されているか確認
        if not any(vars(request.setup_options).values()):
            raise ValueError("セットアップオプションが1つも選択されていません")
        
        logger.info(f"セットアップリクエストの検証成功: {request.request_id}")
        return True
    
    except Exception as e:
        logger.error(f"セットアップリクエスト検証エラー: {str(e)}")
        return False

def calculate_progress(request: SetupRequest) -> float:
    """セットアップ全体の進捗率を計算する"""
    if not request.current_progress:
        return 0.0
    
    total_progress = sum(request.current_progress.values())
    return total_progress / len(request.computers)