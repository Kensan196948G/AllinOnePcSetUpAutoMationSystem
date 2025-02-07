from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from .database import Base

# Enumクラス
class LoginType(str, Enum):
    AD = "AD"
    LOCAL_EXISTING = "LocalExisting"
    LOCAL_NEW = "LocalNew"

class PCSetupStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

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
    setup_desktop_icons = Column(Boolean, default=False)  # デスクトップアイコンの表示設定
    move_vpn_icon = Column(Boolean, default=False)        # インジケーター内のFortiClientVPNを横へ移動
    disable_ipv6 = Column(Boolean, default=False)         # IPv6の無効化
    disable_defender = Column(Boolean, default=False)      # Windows Defenderファイアウォールの無効化
    unpin_mail_store = Column(Boolean, default=False)     # Mail、Storeのピン留めを外す
    setup_edge_defaults = Column(Boolean, default=False)   # Edgeのデフォルトサイト設定
    set_edge_as_default = Column(Boolean, default=False)  # Edgeの既定のブラウザ設定
    setup_default_mail = Column(Boolean, default=False)    # 既定のプログラム設定(メール、Webブラウザ)
    setup_default_pdf = Column(Boolean, default=False)     # 既定のプログラム設定(.pdf、.pdx)

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

    computers = relationship("ComputerInfoDB", back_populates="request")
    setup_options = relationship("SetupOptionsDB", back_populates="request", uselist=False)
    progress_logs = relationship("SetupProgressDB", back_populates="request")

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

    request = relationship("SetupRequestDB", back_populates="progress_logs")

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
    setup_desktop_icons: bool = False    # デスクトップアイコンの表示設定
    move_vpn_icon: bool = False          # インジケーター内のFortiClientVPNを横へ移動
    disable_ipv6: bool = False           # IPv6の無効化
    disable_defender: bool = False        # Windows Defenderファイアウォールの無効化
    unpin_mail_store: bool = False       # Mail、Storeのピン留めを外す
    setup_edge_defaults: bool = False     # Edgeのデフォルトサイト設定
    set_edge_as_default: bool = False    # Edgeの既定のブラウザ設定
    setup_default_mail: bool = False      # 既定のプログラム設定(メール、Webブラウザ)
    setup_default_pdf: bool = False       # 既定のプログラム設定(.pdf、.pdx)

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

class SetupProgress(BaseModel):
    computer_name: str
    task_name: str
    status: str
    progress: float
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ApprovalRequest(BaseModel):
    request_id: str
    approver: str
    approved: bool
    rejection_reason: Optional[str] = None