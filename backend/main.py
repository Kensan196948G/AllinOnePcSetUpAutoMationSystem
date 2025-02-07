from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import subprocess
import logging
from datetime import datetime
import os
from pathlib import Path
import json
import sys

# プロジェクトルートをPythonパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.models import (
    SetupRequest, ComputerInfo, SetupOptions, PCSetupStatus,
    SetupProgress, ApprovalRequest,
    SetupProgressDB, SetupRequestDB, SetupOptionsDB, ComputerInfoDB
)
from backend.utils import parse_csv_data, create_setup_request, validate_setup_request, calculate_progress

# 現在のディレクトリを取得
CURRENT_DIR = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LOGS_DIR = PROJECT_ROOT / "logs"

# ログディレクトリの作成
LOGS_DIR.mkdir(exist_ok=True)

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="PC Setup Automation API",
    description="PCセットアップを自動化するためのRESTful API",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ルートパスでindex.htmlを返す
@app.get("/")
async def read_root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

# スタイルシートを提供
@app.get("/style.css")
async def get_css():
    return FileResponse(str(FRONTEND_DIR / "style.css"), media_type="text/css")

# JavaScriptを提供
@app.get("/script.js")
async def get_js():
    return FileResponse(str(FRONTEND_DIR / "script.js"), media_type="application/javascript")

# サンプルCSVファイルを提供
@app.get("/api/sample-csv")
async def get_sample_csv():
    return FileResponse(
        str(PROJECT_ROOT / "登録ユーザ情報サンプル.csv"),
        media_type="text/csv",
        filename="登録ユーザ情報サンプル.csv"
    )

from sqlalchemy.orm import Session
from backend.database import get_db, engine, Base, SessionLocal

# データベースのテーブルを作成
Base.metadata.create_all(bind=engine)

import asyncio
from backend.errors import PowerShellError, NetworkError, handle_setup_error
from backend.logging_config import log_error
import logging

logger = logging.getLogger(__name__)

async def execute_setup_script(request_id: str, computer: ComputerInfo, options: SetupOptions, retry_count: int = 0):
    """PowerShellスクリプトを実行し、エラー時は自動リトライを行う"""
    try:
        # PowerShellスクリプトのパスを構築
        script_path = PROJECT_ROOT / "scripts" / "remote_setup.ps1"
        
        # スクリプトに渡すパラメータを構築
        params = [
            "-ComputerName", computer.computer_name,
            "-Username", computer.ad_username or computer.local_existing_username or computer.local_new_username
        ]
        
        password = computer.ad_password or computer.local_existing_password or computer.local_new_password
        if password:
            params.extend(["-Password", f"(ConvertTo-SecureString -String '{password}' -AsPlainText -Force)"])
        
        # オプション設定をJSONファイルとして保存
        config_path = LOGS_DIR / f"config_{request_id}_{computer.computer_name}.json"
        with open(config_path, "w") as f:
            json.dump(options.dict(), f)
        params.extend(["-ConfigPath", str(config_path)])
        
        # スクリプトを実行
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)] + params
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # 実行結果を処理
        if process.returncode == 0:
            log_progress(request_id, computer.computer_name, "Setup", "Completed", "セットアップが完了しました", 100.0)
            logger.info(f"セットアップ成功: {computer.computer_name}")
        else:
            error = PowerShellError(
                message="PowerShellスクリプトの実行に失敗しました",
                exit_code=process.returncode,
                stderr=process.stderr,
                command=" ".join(cmd),
                retry_count=retry_count
            )
            
            if error.can_retry():
                logger.warning(f"セットアップ失敗、リトライを試みます: {computer.computer_name} (試行回数: {retry_count + 1})")
                # リトライ前に一時待機
                await asyncio.sleep(min(2 ** retry_count, 30))  # 指数バックオフ
                return await execute_setup_script(request_id, computer, options, retry_count + 1)
            else:
                log_error(logger, error, {"computer_name": computer.computer_name})
                log_progress(request_id, computer.computer_name, "Setup", "Failed", str(error), -1.0)
                raise error
            
    except subprocess.TimeoutExpired:
        error = NetworkError(
            message="PowerShellスクリプトの実行がタイムアウトしました",
            host=computer.computer_name,
            retry_count=retry_count
        )
        
        if error.can_retry():
            logger.warning(f"タイムアウト、リトライを試みます: {computer.computer_name} (試行回数: {retry_count + 1})")
            await asyncio.sleep(min(2 ** retry_count, 30))
            return await execute_setup_script(request_id, computer, options, retry_count + 1)
        else:
            log_error(logger, error, {"computer_name": computer.computer_name})
            log_progress(request_id, computer.computer_name, "Setup", "Failed", str(error), -1.0)
            raise error
            
    except Exception as e:
        error = PowerShellError(
            message="予期せぬエラーが発生しました",
            exit_code=-1,
            stderr=str(e),
            command=" ".join(cmd),
            retry_count=retry_count
        )
        log_error(logger, error, {"computer_name": computer.computer_name})
        log_progress(request_id, computer.computer_name, "Setup", "Error", str(error), -1.0)
        raise error
        log_progress(request_id, computer.computer_name, "Setup", "Error", f"実行エラー: {str(e)}")

def log_progress(request_id: str, computer_name: str, task: str, status: str, message: str, progress_value: float, db: Session = Depends(get_db)):
    """進捗状況をログに記録"""
    # 進捗ログを作成
    progress_log = SetupProgressDB(
        request_id=request_id,
        computer_name=computer_name,
        task_name=task,
        status=status,
        progress=progress_value,
        message=message
    )
    
    # リクエストの進捗状況を更新
    request = db.query(SetupRequestDB).filter(
        SetupRequestDB.request_id == request_id
    ).first()
    
    if request:
        if not request.current_progress:
            request.current_progress = {}
        request.current_progress[computer_name] = progress_value
    
    db.add(progress_log)
    db.commit()

@app.post("/api/setup/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """CSVファイルをアップロードしてコンピュータ情報をパース"""
    try:
        content = await file.read()
        csv_content = content.decode()
        computers = parse_csv_data(csv_content)
        return {"status": "success", "computers": computers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/setup/create")
async def create_setup(
    requester: str = Form(...),
    computers_json: str = Form(...),
    options_json: str = Form(...),
    db: Session = Depends(get_db)
):
    """セットアップリクエストを作成"""
    try:
        # Pydanticモデルの作成
        computers_data = [ComputerInfo(**comp) for comp in json.loads(computers_json)]
        options_data = SetupOptions(**json.loads(options_json))
        
        # リクエストの作成と検証
        request = create_setup_request(requester, computers_data, options_data.dict())
        if not validate_setup_request(request):
            raise HTTPException(status_code=400, detail="無効なセットアップリクエスト")
        
        # データベースモデルの作成
        db_request = SetupRequestDB(
            request_id=request.request_id,
            requester=request.requester,
            status=request.status,
            current_progress={}
        )
        
        # セットアップオプションの保存
        db_options = SetupOptionsDB(
            request_id=request.request_id,
            **options_data.dict()
        )
        
        # コンピュータ情報の保存
        db_computers = [
            ComputerInfoDB(
                request_id=request.request_id,
                **comp.dict()
            )
            for comp in computers_data
        ]
        
        # データベースに保存
        db.add(db_request)
        db.add(db_options)
        db.add_all(db_computers)
        db.commit()
        
        return {"status": "success", "request_id": request.request_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/setup/approve")
async def approve_setup(
    approval: ApprovalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """セットアップリクエストを承認または却下"""
    request = db.query(SetupRequestDB).filter(
        SetupRequestDB.request_id == approval.request_id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")
    
    if request.status != PCSetupStatus.PENDING:
        raise HTTPException(status_code=400, detail="このリクエストは既に処理されています")
    
    try:
        if approval.approved:
            request.status = PCSetupStatus.APPROVED
            request.approved_by = approval.approver
            request.approved_at = datetime.now()
            
            # 各コンピュータに対してセットアップを開始
            computers = db.query(ComputerInfoDB).filter(
                ComputerInfoDB.request_id == request.request_id
            ).all()
            
            setup_options = db.query(SetupOptionsDB).filter(
                SetupOptionsDB.request_id == request.request_id
            ).first()
            
            for computer in computers:
                background_tasks.add_task(
                    execute_setup_script,
                    request.request_id,
                    ComputerInfo(**{
                        k: v for k, v in computer.__dict__.items()
                        if not k.startswith('_')
                    }),
                    SetupOptions(**{
                        k: v for k, v in setup_options.__dict__.items()
                        if not k.startswith('_') and k != 'id' and k != 'request_id'
                    })
                )
        else:
            request.status = PCSetupStatus.REJECTED
            request.rejection_reason = approval.rejection_reason
        
        db.commit()
        return {"status": "success", "request": request}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/setup/{request_id}/status")
async def get_setup_status(request_id: str, db: Session = Depends(get_db)):
    """セットアップの進捗状況を取得"""
    request = db.query(SetupRequestDB).filter(SetupRequestDB.request_id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")
    
    progress = calculate_progress(request)
    logs = db.query(SetupProgressDB).filter(
        SetupProgressDB.request_id == request_id
    ).order_by(SetupProgressDB.timestamp.desc()).all()
    
    return {
        "status": request.status,
        "progress": progress,
        "computer_progress": request.current_progress,
        "logs": [
            SetupProgress(
                computer_name=log.computer_name,
                task_name=log.task_name,
                status=log.status,
                progress=log.progress,
                message=log.message,
                timestamp=log.timestamp
            ) for log in logs
        ]
    }

@app.get("/api/setup/list")
async def list_setup_requests(
    status: Optional[PCSetupStatus] = None,
    requester: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """セットアップリクエストの一覧を取得"""
    query = db.query(SetupRequestDB)
    
    if status:
        query = query.filter(SetupRequestDB.status == status)
    if requester:
        query = query.filter(SetupRequestDB.requester == requester)
    
    requests = query.all()
    return {
        "requests": [
            SetupRequest(
                request_id=req.request_id,
                requester=req.requester,
                computers=[
                    ComputerInfo(**{
                        k: v for k, v in comp.__dict__.items()
                        if not k.startswith('_')
                    }) for comp in req.computers
                ],
                setup_options=SetupOptions(**{
                    k: v for k, v in req.setup_options.__dict__.items()
                    if not k.startswith('_')
                }),
                status=req.status,
                created_at=req.created_at,
                updated_at=req.updated_at,
                approved_by=req.approved_by,
                approved_at=req.approved_at,
                rejection_reason=req.rejection_reason,
                current_progress=req.current_progress
            ) for req in requests
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)