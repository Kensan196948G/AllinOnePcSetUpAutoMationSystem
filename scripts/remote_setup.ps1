param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [SecureString]$Password,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath
)

# ログ機能のインポート
$scriptPath = $PSScriptRoot
. (Join-Path $scriptPath "logging.ps1")

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ExecutionLog -TaskName "Remote Setup" -Status "Error" -Error "このスクリプトは管理者権限で実行する必要があります。"
    exit 1
}

# ヘルパー関数: リモートコマンド実行とログ記録
function Invoke-RemoteCommand {
    param(
        [string]$Command,
        [string]$Description
    )
    
    try {
        Write-ExecutionLog -TaskName "Remote Command" -Status "InProgress" -Error ("実行中: " + $Description)
        
        $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
        $remoteComputer = Join-Path "\\" $ComputerName
        $result = psexec.exe $remoteComputer -u $Username -p $plainPassword powershell.exe -Command $Command
        
        Write-ExecutionLog -TaskName "Remote Command" -Status "Completed" -Error ("完了: " + $Description)
        return $true
    } catch {
        Write-ExecutionLog -TaskName "Remote Command" -Status "Error" -Error ("エラー - " + $Description + ": " + $_.Exception.Message)
        return $false
    }
}

try {
    Write-ExecutionLog -TaskName "Remote Setup" -Status "Started" -Error ("リモートPCセットアップを開始します: " + $ComputerName)

    # 基本的なシステム情報の取得
    Write-ExecutionLog -TaskName "System Info" -Status "InProgress" -Error "システム情報を取得中"
    $systemInfo = Invoke-RemoteCommand -Command {
        $os = Get-WmiObject Win32_OperatingSystem
        $cs = Get-WmiObject Win32_ComputerSystem
        $cpu = Get-WmiObject Win32_Processor
        "OS: " + $os.Caption + "`nメモリ: " + [math]::Round($cs.TotalPhysicalMemory / 1GB, 2) + "GB`nプロセッサ: " + $cpu.Name
    } -Description "システム情報の取得"
    Write-ExecutionLog -TaskName "System Info" -Status "Info" -Error $systemInfo

    # Windows Update設定
    Write-ExecutionLog -TaskName "Windows Update" -Status "InProgress" -Error "Windows Update設定を構成中"
    Invoke-RemoteCommand -Command {
        Set-Service wuauserv -StartupType Automatic
        Start-Service wuauserv
    } -Description "Windows Update設定"

    # セキュリティ設定
    Write-ExecutionLog -TaskName "Security Settings" -Status "InProgress" -Error "セキュリティ設定を構成中"
    Invoke-RemoteCommand -Command {
        Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
        Set-MpPreference -DisableRealtimeMonitoring $false
    } -Description "セキュリティ設定"

    # 設定ファイルがある場合は追加設定を適用
    if ($ConfigPath -and (Test-Path $ConfigPath)) {
        Write-ExecutionLog -TaskName "Custom Config" -Status "InProgress" -Error "カスタム設定を適用中"
        $config = Get-Content $ConfigPath | ConvertFrom-Json
        foreach ($setting in $config.PSObject.Properties) {
            Invoke-RemoteCommand -Command $setting.Value -Description $setting.Name
        }
        Write-ExecutionLog -TaskName "Custom Config" -Status "Completed" -Error "カスタム設定の適用が完了"
    }

    Write-ExecutionLog -TaskName "Remote Setup" -Status "Completed" -Error "セットアップが完了しました"
} catch {
    Write-ExecutionLog -TaskName "Remote Setup" -Status "Error" -Error ("セットアップ中にエラーが発生しました: " + $_.Exception.Message)
    exit 1
}