from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from .database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")

    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return pwd_context.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"

class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    role: str

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Enumクラス
class LoginType(str, Enum):
    AD = "AD"
    LOCAL_EXISTING = "LocalExisting"
    LOCAL_NEW = "LocalNew"

class PCSetupStatus(str, Enum):
    PENDING = "pending"           # 承認待ち
    APPROVED = "approved"         # 承認済み
    REJECTED = "rejected"         # 却下
    IN_PROGRESS = "in_progress"   # 実行中
    COMPLETED = "completed"       # 完了
    FAILED = "failed"            # 失敗
    PARTIALLY_FAILED = "partially_failed"  # 一部失敗
    ROLLBACK = "rollback"        # ロールバック中
    ROLLBACK_FAILED = "rollback_failed"  # ロールバック失敗

class TaskStatus(str, Enum):
    PENDING = "pending"          # 実行待ち
    IN_PROGRESS = "in_progress"  # 実行中
    COMPLETED = "completed"      # 完了
    FAILED = "failed"           # 失敗
    SKIPPED = "skipped"         # スキップ
    WARNING = "warning"         # 警告付きで完了

class ErrorSeverity(str, Enum):
    INFO = "info"           # 情報
    WARNING = "warning"     # 警告
    ERROR = "error"         # エラー
    CRITICAL = "critical"   # 重大

# SQLAlchemyモデル
class ComputerInfoDB(Base):
    __tablename__ = "computers"

    id = Column(Integer, primary_key=True, index=True)
    computer_name = Column(String, index=True)
    ip_address = Column(String)
    login_type = Column(String)
    ad_username = Column(String, nullable=True)
    ad_password = Column(String, nullable=True)
    local_existing_username = Column(String, nullable=True)
    local_existing_password = Column(String, nullable=True)
    full_name = Column(String)
    local_new_username = Column(String, nullable=True)
    local_new_password = Column(String, nullable=True)
    admin_privilege = Column(Boolean, default=False)
    request_id = Column(String, ForeignKey('setup_requests.request_id'))

    request = relationship("SetupRequestDB", back_populates="computers")

class SetupOptionsDB(Base):
    __tablename__ = "setup_options"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey('setup_requests.request_id'))
    
    # OS設定
    setup_desktop_icons = Column(Boolean, default=False)
    move_vpn_icon = Column(Boolean, default=False)
    disable_ipv6 = Column(Boolean, default=False)
    disable_defender = Column(Boolean, default=False)
    unpin_mail_store = Column(Boolean, default=False)
    setup_edge_defaults = Column(Boolean, default=False)
    set_edge_as_default = Column(Boolean, default=False)
    setup_default_mail = Column(Boolean, default=False)
    setup_default_pdf = Column(Boolean, default=False)

    # Microsoft 365
    install_office = Column(Boolean, default=False)
    setup_office_auth = Column(Boolean, default=False)
    configure_office_apps = Column(Boolean, default=False)

    # アプリケーションインストール
    install_dvd_software = Column(Boolean, default=False)
    install_carbon_black = Column(Boolean, default=False)
    install_forticlient_vpn = Column(Boolean, default=False)
    install_ares_standard = Column(Boolean, default=False)
    install_apex_one = Column(Boolean, default=False)
    install_virus_buster = Column(Boolean, default=False)

    # システム更新
    update_office = Column(Boolean, default=False)
    update_windows = Column(Boolean, default=False)
    cleanup_system = Column(Boolean, default=False)
    restart_system = Column(Boolean, default=False)

    request = relationship("SetupRequestDB", back_populates="setup_options")

class SetupRequestDB(Base):
    __tablename__ = "setup_requests"

    request_id = Column(String, primary_key=True, index=True)
    requester = Column(String)
    status = Column(String, default=PCSetupStatus.PENDING)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    current_progress = Column(JSON, default=dict)
    estimated_time = Column(Integer, nullable=True)  # 推定所要時間(分)
    actual_time = Column(Integer, nullable=True)     # 実際の所要時間(分)

    computers = relationship("ComputerInfoDB", back_populates="request")
    setup_options = relationship("SetupOptionsDB", back_populates="request", uselist=False)
    progress_logs = relationship("SetupProgressDB", back_populates="request")
    task_logs = relationship("TaskLogDB", back_populates="request")
    error_logs = relationship("ErrorLogDB", back_populates="request")

class SetupProgressDB(Base):
    __tablename__ = "setup_progress"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey('setup_requests.request_id'))
    computer_name = Column(String)
    task_name = Column(String)
    status = Column(String)
    progress = Column(Float)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # 所要時間(秒)

    request = relationship("SetupRequestDB", back_populates="progress_logs")

class TaskLogDB(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey('setup_requests.request_id'))
    computer_name = Column(String)
    task_name = Column(String)
    status = Column(String)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # 所要時間(秒)
    details = Column(JSON, default=dict)
    error_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)

    request = relationship("SetupRequestDB", back_populates="task_logs")

class ErrorLogDB(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey('setup_requests.request_id'))
    computer_name = Column(String)
    task_name = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    error_code = Column(String)
    error_message = Column(String)
    severity = Column(String)
    details = Column(JSON, default=dict)
    stack_trace = Column(String, nullable=True)
    resolution_steps = Column(JSON, nullable=True)

    request = relationship("SetupRequestDB", back_populates="error_logs")

# Pydanticモデル(スキーマ)
class ComputerInfo(BaseModel):
    computer_name: str
    ip_address: str
    login_type: LoginType
    ad_username: Optional[str] = None
    ad_password: Optional[str] = None
    local_existing_username: Optional[str] = None
    local_existing_password: Optional[str] = None
    full_name: str
    local_new_username: Optional[str] = None
    local_new_password: Optional[str] = None
    admin_privilege: bool = False

class SetupOptions(BaseModel):
    # OS設定
    setup_desktop_icons: bool = False
    move_vpn_icon: bool = False
    disable_ipv6: bool = False
    disable_defender: bool = False
    unpin_mail_store: bool = False
    setup_edge_defaults: bool = False
    set_edge_as_default: bool = False
    setup_default_mail: bool = False
    setup_default_pdf: bool = False

    # Microsoft 365
    install_office: bool = False
    setup_office_auth: bool = False
    configure_office_apps: bool = False

    # アプリケーションインストール
    install_dvd_software: bool = False
    install_carbon_black: bool = False
    install_forticlient_vpn: bool = False
    install_ares_standard: bool = False
    install_apex_one: bool = False
    install_virus_buster: bool = False

    # システム更新
    update_office: bool = False
    update_windows: bool = False
    cleanup_system: bool = False
    restart_system: bool = False

class TaskLog(BaseModel):
    computer_name: str
    task_name: str
    status: TaskStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0

class ErrorLog(BaseModel):
    computer_name: str
    task_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    error_code: str
    error_message: str
    severity: ErrorSeverity
    details: Dict[str, Any] = Field(default_factory=dict)
    stack_trace: Optional[str] = None
    resolution_steps: Optional[List[str]] = None

class SetupRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"REQ{datetime.now().strftime('%Y%m%d%H%M%S')}")
    requester: str
    computers: List[ComputerInfo]
    setup_options: SetupOptions
    status: PCSetupStatus = PCSetupStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    current_progress: Dict[str, float] = Field(default_factory=dict)
    estimated_time: Optional[int] = None
    actual_time: Optional[int] = None

class SetupProgress(BaseModel):
    computer_name: str
    task_name: str
    status: str
    progress: float
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None

class ApprovalRequest(BaseModel):
    request_id: str
    approver: str
    approved: bool
    rejection_reason: Optional[str] = None