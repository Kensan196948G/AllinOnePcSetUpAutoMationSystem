param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [SecureString]$Password,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath,
    
    [Parameter(Mandatory=$false)]
    [switch]$Rollback
)

# ロールバック情報を保存するパス
$rollbackPath = Join-Path $PSScriptRoot "rollback_info"
if (-not (Test-Path $rollbackPath)) {
    New-Item -ItemType Directory -Path $rollbackPath -Force | Out-Null
}

# 各操作のロールバック情報を保存する関数
function Save-RollbackInfo {
    param(
        [string]$Operation,
        [hashtable]$Data
    )
    $rollbackFile = Join-Path $rollbackPath "${ComputerName}_${Operation}.json"
    $Data | ConvertTo-Json | Set-Content $rollbackFile
}

# OS設定を適用する関数
function Set-OSConfiguration {
    param (
        [hashtable]$Config
    )
    
    try {
        Write-ExecutionLog -TaskName "OS Settings" -Status "Started" -Error "OS設定の適用を開始します"
        $rollbackData = @{
            modified = @()
        }

        # デスクトップアイコンの表示設定
        if ($Config.setup_desktop_icons) {
            $originalValue = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel" -Name "{20D04FE0-3AEA-1069-A2D8-08002B30309D}" -ErrorAction SilentlyContinue
            Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel" -Name "{20D04FE0-3AEA-1069-A2D8-08002B30309D}" -Value 0
            $rollbackData.modified += @{
                name = "DesktopIcons"
                path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
                key = "{20D04FE0-3AEA-1069-A2D8-08002B30309D}"
                value = $originalValue
            }
        }

        # IPv6の無効化
        if ($Config.disable_ipv6) {
            $adapters = Get-NetAdapter
            foreach ($adapter in $adapters) {
                $originalState = (Get-NetAdapterBinding -Name $adapter.Name -ComponentID "ms_tcpip6").Enabled
                Disable-NetAdapterBinding -Name $adapter.Name -ComponentID "ms_tcpip6"
                $rollbackData.modified += @{
                    name = "IPv6"
                    adapter = $adapter.Name
                    enabled = $originalState
                }
            }
        }

        # Windows Defenderファイアウォールの無効化
        if ($Config.disable_defender) {
            $originalState = Get-NetFirewallProfile | Select-Object -Property Name, Enabled
            Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
            $rollbackData.modified += @{
                name = "WindowsDefender"
                profiles = $originalState
            }
        }

        # Edgeの設定
        if ($Config.setup_edge_defaults -or $Config.set_edge_as_default) {
            $edgePath = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
            if (Test-Path $edgePath) {
                if ($Config.setup_edge_defaults) {
                    # デフォルトサイトの設定
                    $originalSites = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Edge\TopSites" -ErrorAction SilentlyContinue
                    # Edgeの設定を適用
                    $rollbackData.modified += @{
                        name = "EdgeDefaults"
                        sites = $originalSites
                    }
                }
                
                if ($Config.set_edge_as_default) {
                    # デフォルトブラウザの設定を保存
                    $originalDefault = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice" -Name ProgId -ErrorAction SilentlyContinue
                    # Edgeをデフォルトに設定
                    Start-Process $edgePath -ArgumentList "--make-default-browser" -Wait
                    $rollbackData.modified += @{
                        name = "DefaultBrowser"
                        value = $originalDefault
                    }
                }
            }
        }

        Save-RollbackInfo -Operation "os_settings" -Data $rollbackData
        Write-ExecutionLog -TaskName "OS Settings" -Status "Completed" -Error "OS設定の適用が完了しました"
        return $true
    }
    catch {
        Write-ExecutionLog -TaskName "OS Settings" -Status "Error" -Error "OS設定の適用に失敗しました: $($_.Exception.Message)"
        throw
    }
}

# Microsoft 365の設定を適用する関数
function Set-Office365Configuration {
    param (
        [hashtable]$Config
    )
    
    try {
        Write-ExecutionLog -TaskName "Office 365" -Status "Started" -Error "Microsoft 365の設定を開始します"
        $rollbackData = @{
            installed = @()
            modified = @()
        }

        # Office 365のインストール
        if ($Config.install_office) {
            $setupPath = Join-Path $env:TEMP "Office365Setup"
            New-Item -ItemType Directory -Path $setupPath -Force | Out-Null
            
            # ODTのダウンロードと展開
            $odtUrl = "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB8A7D4A7E/officedeploymenttool_15028-20160.exe"
            $odtPath = Join-Path $setupPath "ODT.exe"
            Invoke-WebRequest -Uri $odtUrl -OutFile $odtPath
            Start-Process -FilePath $odtPath -ArgumentList "/extract:$setupPath" -Wait
            
            # 設定ファイルの作成
            $configXml = @"
<Configuration>
    <Add OfficeClientEdition="64" Channel="Current">
        <Product ID="O365ProPlusRetail">
            <Language ID="ja-jp" />
        </Product>
    </Add>
    <Display Level="None" AcceptEULA="TRUE" />
    <Property Name="AUTOACTIVATE" Value="1" />
</Configuration>
"@
            $configPath = Join-Path $setupPath "config.xml"
            $configXml | Out-File $configPath -Encoding UTF8
            
            # インストールの実行
            $setupExe = Join-Path $setupPath "setup.exe"
            Start-Process -FilePath $setupExe -ArgumentList "/configure `"$configPath`"" -Wait
            
            $rollbackData.installed += "Office365"
        }

        Save-RollbackInfo -Operation "office_setup" -Data $rollbackData
        Write-ExecutionLog -TaskName "Office 365" -Status "Completed" -Error "Microsoft 365の設定が完了しました"
        return $true
    }
    catch {
        Write-ExecutionLog -TaskName "Office 365" -Status "Error" -Error "Microsoft 365の設定に失敗しました: $($_.Exception.Message)"
        throw
    }
}

# アプリケーションのインストールを実行する関数
function Install-Applications {
    param (
        [hashtable]$Config
    )
    
    try {
        Write-ExecutionLog -TaskName "Applications" -Status "Started" -Error "アプリケーションのインストールを開始します"
        $rollbackData = @{
            installed = @()
        }

        # FortiClient VPNのインストール
        if ($Config.install_forticlient_vpn) {
            $vpnSetup = Join-Path $env:TEMP "FortiClientVPNSetup.exe"
            Invoke-WebRequest -Uri "https://filestore.fortinet.com/forticlient/downloads/FortiClientVPNSetup_7.0.exe" -OutFile $vpnSetup
            Start-Process -FilePath $vpnSetup -ArgumentList "/quiet" -Wait
            $rollbackData.installed += "FortiClientVPN"
        }

        # Carbon Blackのインストール
        if ($Config.install_carbon_black) {
            # Carbon Blackのインストールコマンド
            $rollbackData.installed += "CarbonBlack"
        }

        # その他のアプリケーションのインストール
        # ...

        Save-RollbackInfo -Operation "applications" -Data $rollbackData
        Write-ExecutionLog -TaskName "Applications" -Status "Completed" -Error "アプリケーションのインストールが完了しました"
        return $true
    }
    catch {
        Write-ExecutionLog -TaskName "Applications" -Status "Error" -Error "アプリケーションのインストールに失敗しました: $($_.Exception.Message)"
        throw
    }
}

# システム更新を実行する関数
function Update-SystemConfiguration {
    param (
        [hashtable]$Config
    )
    
    try {
        Write-ExecutionLog -TaskName "System Update" -Status "Started" -Error "システム更新を開始します"
        $rollbackData = @{
            modified = @()
        }

        # Windows Updateの実行
        if ($Config.update_windows) {
            Install-Module -Name PSWindowsUpdate -Force
            Get-WindowsUpdate -Install -AcceptAll -AutoReboot:$false
        }

        # システムクリーンアップ
        if ($Config.cleanup_system) {
            # ディスククリーンアップ
            cleanmgr /sagerun:1
            # 一時ファイルの削除
            Remove-Item -Path $env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue
        }

        Save-RollbackInfo -Operation "system_update" -Data $rollbackData
        Write-ExecutionLog -TaskName "System Update" -Status "Completed" -Error "システム更新が完了しました"
        return $true
    }
    catch {
        Write-ExecutionLog -TaskName "System Update" -Status "Error" -Error "システム更新に失敗しました: $($_.Exception.Message)"
        throw
    }
}

# ロールバック処理を実行する関数
function Invoke-Rollback {
    Write-ExecutionLog -TaskName "Rollback" -Status "Started" -Error "ロールバック処理を開始します"
    
    # ロールバックファイルを検索
    Get-ChildItem $rollbackPath -Filter "${ComputerName}_*.json" | Sort-Object LastWriteTime -Descending | ForEach-Object {
        $operation = $_.BaseName -replace "${ComputerName}_"
        $rollbackData = Get-Content $_.FullName | ConvertFrom-Json
        
        try {
            switch ($operation) {
                "applications" {
                    # インストールされたソフトウェアのアンインストール
                    foreach ($software in $rollbackData.installed) {
                        Write-ExecutionLog -TaskName "Rollback" -Status "InProgress" -Error "アンインストール中: $software"
                        switch ($software) {
                            "FortiClientVPN" {
                                Start-Process "msiexec.exe" -ArgumentList "/x {84AC8749-B1E5-4A7D-9D19-F86D56B78F4F} /quiet" -Wait
                            }
                            "Office365" {
                                $setupPath = Join-Path $env:TEMP "Office365Setup"
                                $setupExe = Join-Path $setupPath "setup.exe"
                                if (Test-Path $setupExe) {
                                    Start-Process -FilePath $setupExe -ArgumentList "/uninstall ProPlus /quiet" -Wait
                                }
                            }
                            # 他のソフトウェアのアンインストール処理
                        }
                    }
                }
                "os_settings" {
                    # 変更された設定を元に戻す
                    foreach ($setting in $rollbackData.modified) {
                        Write-ExecutionLog -TaskName "Rollback" -Status "InProgress" -Error "設定を復元中: $($setting.name)"
                        switch ($setting.name) {
                            "DesktopIcons" {
                                Set-ItemProperty -Path $setting.path -Name $setting.key -Value $setting.value
                            }
                            "IPv6" {
                                Enable-NetAdapterBinding -Name $setting.adapter -ComponentID "ms_tcpip6"
                            }
                            "WindowsDefender" {
                                foreach ($profile in $setting.profiles) {
                                    Set-NetFirewallProfile -Name $profile.Name -Enabled $profile.Enabled
                                }
                            }
                            # 他の設定の復元処理
                        }
                    }
                }
                default {
                    Write-ExecutionLog -TaskName "Rollback" -Status "Warning" -Error "未知の操作: $operation"
                }
            }
        }
        catch {
            Write-ExecutionLog -TaskName "Rollback" -Status "Error" -Error "ロールバック失敗 - $operation: $($_.Exception.Message)"
            throw
        }
    }
    
    Write-ExecutionLog -TaskName "Rollback" -Status "Completed" -Error "ロールバック処理が完了しました"
}

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

# メイン処理を実行する関数
function Start-Setup {
    param (
        [string]$ConfigPath
    )
    
    try {
        Write-ExecutionLog -TaskName "Setup" -Status "Started" -Error "セットアップを開始します"
        
        # 設定ファイルの読み込み
        if (-not (Test-Path $ConfigPath)) {
            throw "設定ファイルが見つかりません: $ConfigPath"
        }
        $config = Get-Content $ConfigPath | ConvertFrom-Json
        
        # リモート接続の確認
        $credential = New-Object System.Management.Automation.PSCredential($Username, $Password)
        if (-not (Test-WSMan -ComputerName $ComputerName -Credential $credential -ErrorAction SilentlyContinue)) {
            throw "リモートコンピュータに接続できません: $ComputerName"
        }
        
        if ($Rollback) {
            # ロールバックモード
            Invoke-Rollback
        }
        else {
            # セットアップモード
            # OS設定
            if (-not (Set-OSConfiguration -Config $config)) {
                throw "OS設定の適用に失敗しました"
            }
            
            # Microsoft 365
            if (-not (Set-Office365Configuration -Config $config)) {
                throw "Microsoft 365の設定に失敗しました"
            }
            
            # アプリケーションインストール
            if (-not (Install-Applications -Config $config)) {
                throw "アプリケーションのインストールに失敗しました"
            }
            
            # システム更新
            if (-not (Update-SystemConfiguration -Config $config)) {
                throw "システム更新に失敗しました"
            }
            
            # 再起動が必要な場合
            if ($config.restart_system) {
                Write-ExecutionLog -TaskName "Setup" -Status "InProgress" -Error "システムを再起動します"
                Restart-Computer -ComputerName $ComputerName -Force -Wait
            }
        }
        
        Write-ExecutionLog -TaskName "Setup" -Status "Completed" -Error "セットアップが完了しました"
        return $true
    }
    catch {
        Write-ExecutionLog -TaskName "Setup" -Status "Error" -Error "セットアップに失敗しました: $($_.Exception.Message)"
        
        if (-not $Rollback) {
            Write-ExecutionLog -TaskName "Setup" -Status "InProgress" -Error "ロールバックを開始します"
            try {
                Invoke-Rollback
            }
            catch {
                Write-ExecutionLog -TaskName "Setup" -Status "Error" -Error "ロールバックに失敗しました: $($_.Exception.Message)"
            }
        }
        
        throw
    }
}

# スクリプトのメイン処理
try {
    if (-not (Start-Setup -ConfigPath $ConfigPath)) {
        exit 1
    }
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}