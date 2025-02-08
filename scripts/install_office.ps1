[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Password,

    [Parameter(Mandatory=$false)]
    [string]$Channel = "Current",  # Current, MonthlyEnterprise, SemiAnnual

    [Parameter(Mandatory=$false)]
    [string]$Language = "ja-JP"
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

    # Office 365インストールスクリプトブロック
    $scriptBlock = {
        param($Channel, $Language)
        
        try {
            # 作業ディレクトリの作成
            $workDir = "C:\Office365Install"
            New-Item -ItemType Directory -Path $workDir -Force | Out-Null
            Set-Location $workDir

            # ODTのダウンロード
            $odtUrl = "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB8A7D4A7E/officedeploymenttool_15726-20202.exe"
            $odtFile = Join-Path $workDir "ODT.exe"
            Invoke-WebRequest -Uri $odtUrl -OutFile $odtFile

            # ODTの展開
            Start-Process -FilePath $odtFile -ArgumentList "/extract:$workDir /quiet" -Wait

            # 設定XMLの作成
            $configXml = @"
<Configuration>
    <Add OfficeClientEdition="64" Channel="$Channel">
        <Product ID="O365ProPlusRetail">
            <Language ID="$Language" />
            <ExcludeApp ID="Groove" />
            <ExcludeApp ID="Lync" />
        </Product>
    </Add>
    <RemoveMSI />
    <Display Level="None" AcceptEULA="TRUE" />
    <Property Name="AUTOACTIVATE" Value="1" />
</Configuration>
"@
            $configXml | Out-File -FilePath "$workDir\config.xml" -Encoding UTF8

            # 既存のOfficeを確認
            $installed = Get-WmiObject -Class Win32_Product | Where-Object { 
                $_.Name -like "*Microsoft Office*" -or 
                $_.Name -like "*Microsoft 365*" 
            }

            if ($installed) {
                # 既存のOfficeをアンインストール
                foreach ($app in $installed) {
                    $app.Uninstall()
                }
            }

            # Office 365のインストール
            Start-Process -FilePath "setup.exe" -ArgumentList "/configure config.xml" -Wait -NoNewWindow

            # インストール結果の確認
            $officeApps = Get-WmiObject -Class Win32_Product | Where-Object { 
                $_.Name -like "*Microsoft Office*" -or 
                $_.Name -like "*Microsoft 365*" 
            }

            if ($officeApps) {
                return @{
                    "status" = "success"
                    "message" = "Microsoft 365のインストールが完了しました"
                    "installed_apps" = ($officeApps | Select-Object Name, Version | ForEach-Object { 
                        @{ 
                            "name" = $_.Name
                            "version" = $_.Version
                        }
                    })
                }
            }
            else {
                throw "インストールの確認に失敗しました"
            }
        }
        catch {
            throw "Microsoft 365のインストール中にエラーが発生しました: $_"
        }
        finally {
            # 作業ディレクトリのクリーンアップ
            if (Test-Path $workDir) {
                Remove-Item -Path $workDir -Recurse -Force
            }
        }
    }

    # スクリプトブロックの実行
    $remoteResult = Invoke-Command -Session $session -ScriptBlock $scriptBlock -ArgumentList $Channel, $Language

    # 結果の設定
    $result.success = $true
    $result.message = $remoteResult.message
    $result.details = @{
        "installed_apps" = $remoteResult.installed_apps
        "computer" = $ComputerName
        "channel" = $Channel
        "language" = $Language
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