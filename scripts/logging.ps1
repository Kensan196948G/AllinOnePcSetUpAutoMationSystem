# ログファイルのパス設定
$script:LogFile = Join-Path $PSScriptRoot "..\logs\execution_log.txt"

# ログディレクトリが存在しない場合は作成
$logDir = Split-Path $script:LogFile -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-ExecutionLog {
    <#
    .SYNOPSIS
        実行ログを記録する関数
    .DESCRIPTION
        指定されたタスク名とステータスをタイムスタンプ付きでログファイルに記録します
    .PARAMETER TaskName
        実行中のタスク名
    .PARAMETER Status
        タスクの状態
    .PARAMETER Error
        エラーメッセージ(オプション)
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$TaskName,
        
        [Parameter(Mandatory=$true)]
        [string]$Status,
        
        [Parameter(Mandatory=$false)]
        [string]$Error
    )

    # タイムスタンプの生成
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # ログメッセージの作成
    $logMessage = "$timestamp - Task: $TaskName - Status: $Status"
    if ($Error) {
        $logMessage += " - Error: $Error"
    }

    # ログの出力(コンソールとファイル)
    Write-Host $logMessage
    Add-Content -Path $script:LogFile -Value $logMessage

    # エラーの場合はエラーログも出力
    if ($Status -eq "Error") {
        Write-Error $logMessage
    }
}

function Get-ExecutionLog {
    <#
    .SYNOPSIS
        実行ログを取得する関数
    .DESCRIPTION
        ログファイルの内容を取得します
    #>
    if (Test-Path $script:LogFile) {
        Get-Content $script:LogFile
    }
}

function Clear-ExecutionLog {
    <#
    .SYNOPSIS
        実行ログをクリアする関数
    .DESCRIPTION
        ログファイルの内容をクリアします
    #>
    if (Test-Path $script:LogFile) {
        Clear-Content $script:LogFile
        Write-ExecutionLog "LogManagement" "Log cleared"
    }
}

# エクスポートする関数
Export-ModuleMember -Function Write-ExecutionLog, Get-ExecutionLog, Clear-ExecutionLog