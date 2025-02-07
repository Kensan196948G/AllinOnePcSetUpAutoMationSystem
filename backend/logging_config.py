import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any

# ログディレクトリの設定
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ログファイルのパス設定
ERROR_LOG_PATH = LOGS_DIR / "error.log"
SETUP_LOG_PATH = LOGS_DIR / "setup.log"
DEBUG_LOG_PATH = LOGS_DIR / "debug.log"

class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # エラー情報の追加
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # カスタム属性の追加
        if hasattr(record, "error_info"):
            log_data["error_info"] = record.error_info

        return json.dumps(log_data, ensure_ascii=False)

def setup_logging():
    """ロギングの設定"""
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # エラーログの設定
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_PATH,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # セットアップログの設定
    setup_handler = logging.handlers.RotatingFileHandler(
        SETUP_LOG_PATH,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    setup_handler.setLevel(logging.INFO)
    setup_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(setup_handler)

    # デバッグログの設定
    debug_handler = logging.handlers.RotatingFileHandler(
        DEBUG_LOG_PATH,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(debug_handler)

    # コンソール出力の設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    root_logger.addHandler(console_handler)

def log_error(logger: logging.Logger, error: Exception, additional_info: Dict[str, Any] = None):
    """エラーログを記録する共通関数"""
    error_info = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
    }
    
    if hasattr(error, "to_dict"):
        error_info.update(error.to_dict())
    
    if additional_info:
        error_info.update(additional_info)
    
    logger.error(
        f"エラーが発生しました: {error}",
        extra={"error_info": error_info},
        exc_info=True
    )

# 初期化時にロギング設定を適用
setup_logging()