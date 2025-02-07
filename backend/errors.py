from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

class ErrorSeverity(str, Enum):
    """エラーの重大度を定義"""
    CRITICAL = "critical"  # システム全体に影響するエラー
    ERROR = "error"       # 特定の処理が失敗するエラー
    WARNING = "warning"   # 警告レベルのエラー
    INFO = "info"        # 情報レベルのエラー

class ErrorCategory(str, Enum):
    """エラーのカテゴリを定義"""
    SYSTEM = "system"           # システム関連のエラー
    DATABASE = "database"       # データベース関連のエラー
    NETWORK = "network"         # ネットワーク関連のエラー
    AUTHENTICATION = "auth"     # 認証関連のエラー
    VALIDATION = "validation"   # バリデーション関連のエラー
    SETUP = "setup"            # セットアップ処理関連のエラー
    POWERSHELL = "powershell"  # PowerShell実行関連のエラー

class SetupError(Exception):
    """セットアップ処理に関するエラーの基本クラス"""
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        timestamp: datetime = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.error_code = error_code
        self.details = details or {}
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """エラー情報を辞書形式で返す"""
        return {
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
            "error_code": self.error_code,
            "details": self.details,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timestamp": self.timestamp.isoformat()
        }

    def can_retry(self) -> bool:
        """リトライ可能かどうかを判定"""
        return self.retry_count < self.max_retries

    def increment_retry(self):
        """リトライ回数をインクリメント"""
        self.retry_count += 1

class ValidationError(SetupError):
    """バリデーションエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.VALIDATION,
            error_code="VALIDATION_ERROR",
            details=details,
            max_retries=0  # バリデーションエラーはリトライしない
        )

class PowerShellError(SetupError):
    """PowerShell実行エラー"""
    def __init__(
        self,
        message: str,
        exit_code: int,
        stderr: str,
        command: str,
        retry_count: int = 0
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.POWERSHELL,
            error_code=f"POWERSHELL_ERROR_{exit_code}",
            details={
                "exit_code": exit_code,
                "stderr": stderr,
                "command": command
            },
            retry_count=retry_count
        )

class NetworkError(SetupError):
    """ネットワークエラー"""
    def __init__(
        self,
        message: str,
        host: str,
        retry_count: int = 0
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK,
            error_code="NETWORK_ERROR",
            details={"host": host},
            retry_count=retry_count
        )

class DatabaseError(SetupError):
    """データベースエラー"""
    def __init__(
        self,
        message: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE,
            error_code="DATABASE_ERROR",
            details={"operation": operation, **(details or {})},
            max_retries=0  # データベースエラーは即座に報告
        )

def handle_setup_error(error: SetupError) -> Dict[str, Any]:
    """エラーハンドリングの共通処理"""
    error_info = error.to_dict()
    
    # エラーの重大度に応じたレスポンス
    if error.severity == ErrorSeverity.CRITICAL:
        status_code = 500  # Internal Server Error
    elif error.severity == ErrorSeverity.ERROR:
        status_code = 400  # Bad Request
    else:
        status_code = 200  # OK (Warning/Info)
    
    return {
        "status_code": status_code,
        "error": error_info
    }