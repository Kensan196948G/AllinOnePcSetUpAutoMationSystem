[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Password,

    [Parameter(Mandatory=$false)]
    [string]$InstallerUrl = "",  # Carbon BlackインストーラーのダウンロードURL

    [Parameter(Mandatory=$false)]
    [string]$CompanyCode = ""    # 会社固有のインストールコード
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

    # Carbon Blackインストールスクリプトブロック
    $scriptBlock = {
        param($InstallerUrl, $CompanyCode)
        
        try {
            # 作業ディレクトリの作成
            $workDir = "C:\CarbonBlackInstall"
            New-Item -ItemType Directory -Path $workDir -Force | Out-Null
            Set-Location $workDir

            # インストーラーのダウンロード
            $installerPath = Join-Path $workDir "CarbonBlack_installer.msi"
            if ($InstallerUrl) {
                Invoke-WebRequest -Uri $InstallerUrl -OutFile $installerPath
            }
            else {
                throw "インストーラーのURLが指定されていません"
            }

            # 既存のCarbon Blackを確認
            $installed = Get-WmiObject -Class Win32_Product | Where-Object { 
                $_.Name -like "*Carbon Black*" 
            }

            if ($installed) {
                # 既存のCarbon Blackをアンインストール
                foreach ($app in $installed) {
                    $app.Uninstall()
                }
                Start-Sleep -Seconds 10  # アンインストール完了を待機
            }

            # インストールパラメータの設定
            $installParams = @(
                "/i"
                $installerPath
                "/qn"  # サイレントインストール
                "COMPANY_CODE=$CompanyCode"
                "ALLUSERS=1"
                "/l*v $workDir\install_log.txt"  # 詳細なログを記録
            )

            # Carbon Blackのインストール
            $process = Start-Process "msiexec.exe" -ArgumentList $installParams -Wait -PassThru -NoNewWindow

            if ($process.ExitCode -ne 0) {
                $logContent = Get-Content "$workDir\install_log.txt" -ErrorAction SilentlyContinue
                throw "インストールに失敗しました。終了コード: $($process.ExitCode)`nログ: $logContent"
            }

            # インストール結果の確認
            $cbApp = Get-WmiObject -Class Win32_Product | Where-Object { 
                $_.Name -like "*Carbon Black*" 
            }

            if ($cbApp) {
                # サービスの状態を確認
                $service = Get-Service -Name "CarbonBlack" -ErrorAction SilentlyContinue
                $serviceStatus = if ($service) { $service.Status } else { "NotFound" }

                return @{
                    "status" = "success"
                    "message" = "Carbon Blackのインストールが完了しました"
                    "app_info" = @{
                        "name" = $cbApp.Name
                        "version" = $cbApp.Version
                        "service_status" = $serviceStatus
                    }
                }
            }
            else {
                throw "インストールの確認に失敗しました"
            }
        }
        catch {
            throw "Carbon Blackのインストール中にエラーが発生しました: $_"
        }
        finally {
            # 作業ディレクトリのクリーンアップ
            if (Test-Path $workDir) {
                Remove-Item -Path $workDir -Recurse -Force
            }
        }
    }

    # スクリプトブロックの実行
    $remoteResult = Invoke-Command -Session $session -ScriptBlock $scriptBlock -ArgumentList $InstallerUrl, $CompanyCode

    # 結果の設定
    $result.success = $true
    $result.message = $remoteResult.message
    $result.details = @{
        "app_info" = $remoteResult.app_info
        "computer" = $ComputerName
        "company_code" = $CompanyCode
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