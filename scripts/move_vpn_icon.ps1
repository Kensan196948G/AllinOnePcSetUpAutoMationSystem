[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Password
)

# 結果を格納するハッシュテーブル
$result = @{
    "success" = $false
    "message" = ""
    "details" = @{}
}

try {
    # 資格情報の作成
    $securePassword = ConvertTo-SecureString -String $Password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential ($Username, $securePassword)

    # リモートセッションの作成
    $session = New-PSSession -ComputerName $ComputerName -Credential $credential

    # VPNアイコン移動のスクリプトブロック
    $scriptBlock = {
        try {
            # FortiClientのレジストリパス
            $fortiClientPath = "HKLM:\SOFTWARE\Fortinet\FortiClient"
            
            if (!(Test-Path $fortiClientPath)) {
                throw "FortiClientのレジストリが見つかりません"
            }

            # システムトレイの設定パス
            $traySettingsPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\TrayNotify"
            
            if (!(Test-Path $traySettingsPath)) {
                New-Item -Path $traySettingsPath -Force | Out-Null
            }

            # アイコンの位置設定
            $iconPositions = @{
                "FortiTray" = @{
                    "Position" = "Right"
                    "Order" = 1
                }
            }

            # レジストリ値の設定
            Set-ItemProperty -Path $traySettingsPath -Name "IconStreams" -Value ([byte[]]@(0)) -Type Binary
            Set-ItemProperty -Path $traySettingsPath -Name "PastIconsStream" -Value ([byte[]]@(0)) -Type Binary

            # エクスプローラーの再起動
            Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            Start-Process explorer

            # FortiClientサービスの再起動
            Restart-Service -Name "FortiClientSvc" -Force -ErrorAction SilentlyContinue

            return @{
                "status" = "success"
                "message" = "FortiClient VPNアイコンの位置を設定しました"
                "settings" = $iconPositions
            }
        }
        catch {
            throw "VPNアイコンの設定中にエラーが発生しました: $_"
        }
    }

    # スクリプトブロックの実行
    $remoteResult = Invoke-Command -Session $session -ScriptBlock $scriptBlock

    # 結果の設定
    $result.success = $true
    $result.message = $remoteResult.message
    $result.details = @{
        "settings" = $remoteResult.settings
        "computer" = $ComputerName
        "timestamp" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
}
catch {
    $result.message = "エラーが発生しました: $_"
}
finally {
    # セッションの終了
    if ($session) {
        Remove-PSSession $session
    }
}

# 結果をJSON形式で出力
$result | ConvertTo-Json -Depth 10