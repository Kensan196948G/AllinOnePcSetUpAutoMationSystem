import csv
from io import StringIO
from typing import List, Dict, Any
import logging
from datetime import datetime
from pathlib import Path

from .models import ComputerInfo, LoginType, SetupRequest, SetupOptions

# ログディレクトリの設定
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"
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

def parse_csv_data(csv_content: str) -> List[ComputerInfo]:
    """
    CSVファイルの内容をパースしてComputerInfoオブジェクトのリストを返す
    6行目からデータを読み込む
    
    Args:
        csv_content (str): CSVファイルの内容
    
    Returns:
        List[ComputerInfo]: パースされたコンピュータ情報のリスト
    
    Raises:
        ValueError: CSVの形式が不正な場合
    """
    try:
        # CSVの行を分割
        lines = csv_content.splitlines()
        
        # 10行目以降のデータを取得
        if len(lines) < 10:
            raise ValueError("CSVファイルのデータが不足しています")
        
        data_lines = lines[9:]  # 10行目から開始(0ベース)
        
        # ヘッダーを定義
        headers = [
            "computer_name", "ip_address", "login_type",
            "ad_username", "ad_password", "local_existing_username",
            "local_existing_password", "full_name", "local_new_username",
            "local_new_password", "admin_privilege"
        ]
        
        # DictReaderでパース
        reader = csv.DictReader(StringIO('\n'.join(data_lines)), fieldnames=headers)
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
            
            login_type = login_type_map.get(row['login_type'])
            if not login_type:
                raise ValueError(f"不正なログイン種別です: {row['login_type']}\n有効な値: AD, 既存ローカル, 新規ローカル")
            
            # ComputerInfoオブジェクトの作成
            computer = ComputerInfo(
                computer_name=row['computer_name'],
                ip_address=row['ip_address'],
                login_type=login_type,
                ad_username=row['ad_username'],
                ad_password=row['ad_password'],
                local_existing_username=row['local_existing_username'],
                local_existing_password=row['local_existing_password'],
                full_name=row['full_name'],
                local_new_username=row['local_new_username'],
                local_new_password=row['local_new_password'],
                admin_privilege=row['admin_privilege'].lower() == 'yes'
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
    """
    セットアップリクエストを作成する
    
    Args:
        requester (str): 申請者名
        computers (List[ComputerInfo]): セットアップ対象PCのリスト
        setup_options (Dict[str, bool]): セットアップオプションの設定
    
    Returns:
        SetupRequest: 作成されたセットアップリクエスト
    """
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
    """
    セットアップリクエストのバリデーションを行う
    
    Args:
        request (SetupRequest): 検証するセットアップリクエスト
    
    Returns:
        bool: バリデーション結果
    """
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
    """
    セットアップ全体の進捗率を計算する
    
    Args:
        request (SetupRequest): 進捗を計算するセットアップリクエスト
    
    Returns:
        float: 全体の進捗率(0-100)
    """
    if not request.current_progress:
        return 0.0
    
    total_progress = sum(request.current_progress.values())
    return total_progress / len(request.computers)