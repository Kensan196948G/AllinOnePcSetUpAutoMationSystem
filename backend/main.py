from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import logging
from logging.config import dictConfig
import json

from .database import get_db
from .models import SetupRequestDB, SetupProgressDB, ComputerInfoDB, SetupOptionsDB
from .auth import get_current_active_user
from .utils import generate_request_id
from .logging_config import logging_config

# ロギング設定
dictConfig(logging_config)
logger = logging.getLogger("backend")

app = FastAPI(title="PC Setup Automation System")

def log_progress(
    request_id: str,
    computer_name: str,
    task: str,
    status: str,
    message: str,
    progress_value: float,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    duration: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """進捗状況をログに記録"""
    # 進捗ログを作成
    progress_log = SetupProgressDB(
        request_id=request_id,
        computer_name=computer_name,
        task_name=task,
        status=status,
        progress=progress_value,
        message=message,
        start_time=start_time,
        end_time=end_time,
        duration=duration
    )
    
    # リクエストの進捗状況を更新
    request = db.query(SetupRequestDB).filter(
        SetupRequestDB.request_id == request_id
    ).first()
    
    if request:
        if not request.current_progress:
            request.current_progress = {}
        request.current_progress[computer_name] = progress_value
        
        # 所要時間の更新
        if duration and status in ["Completed", "Failed"]:
            if not request.actual_time:
                request.actual_time = 0
            request.actual_time += duration
    
    db.add(progress_log)
    db.commit()

async def execute_setup_tasks(
    request_id: str,
    computer_info: ComputerInfoDB,
    setup_options: SetupOptionsDB,
    db: Session
):
    """セットアップタスクを実行"""
    try:
        start_time = datetime.now()
        total_tasks = len([opt for opt in setup_options.dict().values() if opt])
        completed_tasks = 0

        # 初期状態を記録
        log_progress(
            request_id=request_id,
            computer_name=computer_info.computer_name,
            task="setup_initialization",
            status="Started",
            message="セットアップを開始します",
            progress_value=0.0,
            start_time=start_time,
            db=db
        )

        # OS設定タスク
        if setup_options.setup_desktop_icons:
            await execute_task(
                "setup_desktop_icons",
                "デスクトップアイコンの表示設定",
                request_id,
                computer_info,
                db,
                completed_tasks,
                total_tasks
            )
            completed_tasks += 1

        if setup_options.move_vpn_icon:
            await execute_task(
                "move_vpn_icon",
                "FortiClientVPNアイコンの移動",
                request_id,
                computer_info,
                db,
                completed_tasks,
                total_tasks
            )
            completed_tasks += 1

        # Microsoft 365関連タスク
        if setup_options.install_office:
            await execute_task(
                "install_office",
                "Microsoft 365のインストール",
                request_id,
                computer_info,
                db,
                completed_tasks,
                total_tasks
            )
            completed_tasks += 1

        # アプリケーションインストール
        if setup_options.install_carbon_black:
            await execute_task(
                "install_carbon_black",
                "Carbon Blackのインストール",
                request_id,
                computer_info,
                db,
                completed_tasks,
                total_tasks
            )
            completed_tasks += 1

        # 完了状態を記録
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())
        log_progress(
            request_id=request_id,
            computer_name=computer_info.computer_name,
            task="setup_completion",
            status="Completed",
            message="セットアップが完了しました",
            progress_value=100.0,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            db=db
        )

    except Exception as e:
        logger.error(f"セットアップ実行中にエラーが発生: {str(e)}", exc_info=True)
        log_progress(
            request_id=request_id,
            computer_name=computer_info.computer_name,
            task="setup_error",
            status="Failed",
            message=f"エラーが発生しました: {str(e)}",
            progress_value=0.0,
            db=db
        )
        raise

async def execute_task(
    task_id: str,
    task_name: str,
    request_id: str,
    computer_info: ComputerInfoDB,
    setup_options: SetupOptionsDB,
    db: Session,
    completed_tasks: int,
    total_tasks: int
):
    """個別のタスクを実行"""
    try:
        start_time = datetime.now()
        progress = (completed_tasks / total_tasks) * 100

        # タスク開始を記録
        log_progress(
            request_id=request_id,
            computer_name=computer_info.computer_name,
            task=task_id,
            status="In Progress",
            message=f"{task_name}を実行中...",
            progress_value=progress,
            start_time=start_time,
            db=db
        )

        # PowerShellスクリプトの実行
        from .utils import execute_setup_task
        success, message, result = await execute_setup_task(
            task_id,
            computer_info,
            setup_options.dict()
        )

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        if success:
            # タスク完了を記録
            log_progress(
                request_id=request_id,
                computer_name=computer_info.computer_name,
                task=task_id,
                status="Completed",
                message=f"{task_name}が完了しました: {message}",
                progress_value=progress + (100 / total_tasks),
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                db=db
            )
        else:
            # エラーを記録
            log_progress(
                request_id=request_id,
                computer_name=computer_info.computer_name,
                task=task_id,
                status="Failed",
                message=f"{task_name}の実行中にエラーが発生: {message}",
                progress_value=progress,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                db=db
            )
            raise Exception(message)

    except Exception as e:
        logger.error(f"タスク実行中にエラーが発生: {str(e)}", exc_info=True)
        log_progress(
            request_id=request_id,
            computer_name=computer_info.computer_name,
            task=task_id,
            status="Failed",
            message=f"{task_name}の実行中にエラーが発生: {str(e)}",
            progress_value=progress,
            db=db
        )
        raise

@app.post("/api/setup/request")
async def create_setup_request(
    background_tasks: BackgroundTasks,
    computer_info: ComputerInfoDB,
    setup_options: SetupOptionsDB,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セットアップリクエストを作成"""
    try:
        request_id = generate_request_id()
        
        # リクエストをデータベースに保存
        setup_request = SetupRequestDB(
            request_id=request_id,
            requester_id=current_user.id,
            computer_info=computer_info,
            setup_options=setup_options,
            status="Pending",
            request_date=datetime.now()
        )
        db.add(setup_request)
        db.commit()

        # バックグラウンドでセットアップタスクを実行
        background_tasks.add_task(
            execute_setup_tasks,
            request_id,
            computer_info,
            setup_options,
            db
        )

        return {"request_id": request_id, "message": "セットアップリクエストを受け付けました"}

    except Exception as e:
        logger.error(f"セットアップリクエスト作成中にエラーが発生: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"セットアップリクエストの作成に失敗しました: {str(e)}"
        )

@app.get("/api/setup/progress/{request_id}")
async def get_setup_progress(
    request_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セットアップの進捗状況を取得"""
    try:
        # リクエストの存在確認
        request = db.query(SetupRequestDB).filter(
            SetupRequestDB.request_id == request_id
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="指定されたリクエストが見つかりません"
            )

        # 進捗ログの取得
        progress_logs = db.query(SetupProgressDB).filter(
            SetupProgressDB.request_id == request_id
        ).order_by(SetupProgressDB.start_time.desc()).all()

        return {
            "request_id": request_id,
            "status": request.status,
            "current_progress": request.current_progress,
            "actual_time": request.actual_time,
            "progress_logs": [log.__dict__ for log in progress_logs]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"進捗状況の取得中にエラーが発生: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"進捗状況の取得に失敗しました: {str(e)}"
        )

@app.get("/api/setup/requests")
async def get_setup_requests(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セットアップリクエスト一覧を取得"""
    try:
        # ユーザーの権限に応じてリクエストを取得
        if current_user.role == "admin":
            requests = db.query(SetupRequestDB).all()
        else:
            requests = db.query(SetupRequestDB).filter(
                SetupRequestDB.requester_id == current_user.id
            ).all()

        return {
            "requests": [request.__dict__ for request in requests]
        }

    except Exception as e:
        logger.error(f"リクエスト一覧の取得中にエラーが発生: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"リクエスト一覧の取得に失敗しました: {str(e)}"
        )