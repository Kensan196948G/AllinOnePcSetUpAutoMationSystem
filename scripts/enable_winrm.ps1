# ログ機能のインポート
. (Join-Path $PSScriptRoot "logging.ps1")

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ExecutionLog "WinRM Setup" "Error" "このスクリプトは管理者権限で実行する必要があります。"
    exit 1
}

try {
    Write-ExecutionLog "WinRM Setup" "Started" "WinRMの設定を開始します"

    # WinRMサービスの起動と自動起動設定
    Write-ExecutionLog "WinRM Service" "InProgress" "WinRMサービスを設定中"
    Set-Service -Name WinRM -StartupType Automatic
    Start-Service -Name WinRM
    Write-ExecutionLog "WinRM Service" "Completed" "WinRMサービスの設定が完了"

    # WinRM基本設定の実行
    Write-ExecutionLog "WinRM Config" "InProgress" "WinRM基本設定を実行中"
    winrm quickconfig -force
    Write-ExecutionLog "WinRM Config" "Completed" "WinRM基本設定が完了"

    # リモート接続の許可設定
    Write-ExecutionLog "WinRM TrustedHosts" "InProgress" "リモート接続の許可設定を構成中"
    Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
    Write-ExecutionLog "WinRM TrustedHosts" "Completed" "リモート接続の許可設定が完了"

    # 設定の確認
    Write-ExecutionLog "WinRM Verification" "InProgress" "WinRMの設定を確認中"
    $service = Get-Service WinRM
    $trustedHosts = Get-Item WSMan:\localhost\Client\TrustedHosts
    Write-ExecutionLog "WinRM Status" "Info" "WinRMサービスの状態: $($service.Status)"
    Write-ExecutionLog "WinRM TrustedHosts" "Info" "TrustedHosts設定: $($trustedHosts.Value)"

    Write-ExecutionLog "WinRM Setup" "Completed" "WinRMの設定が完了しました"
} catch {
    Write-ExecutionLog "WinRM Setup" "Error" "エラーが発生しました: $_"
    exit 1
}