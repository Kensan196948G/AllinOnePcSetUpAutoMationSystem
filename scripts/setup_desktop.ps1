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

    # デスクトップアイコンの設定スクリプトブロック
    $scriptBlock = {
        try {
            # デスクトップアイコン設定の変更
            $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
            
            # キーが存在しない場合は作成
            if (!(Test-Path $path)) {
                New-Item -Path $path -Force | Out-Null
            }

            # デスクトップアイコンの表示設定
            $desktopIcons = @{
                "{20D04FE0-3AEA-1069-A2D8-08002B30309D}" = 0  # This PC
                "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}" = 0  # Control Panel
                "{59031a47-3f72-44a7-89c5-5595fe6b30ee}" = 0  # User Files
                "{645FF040-5081-101B-9F08-00AA002F954E}" = 0  # Recycle Bin
                "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}" = 0  # Network
            }

            # 各アイコンの設定を適用
            foreach ($icon in $desktopIcons.GetEnumerator()) {
                Set-ItemProperty -Path $path -Name $icon.Key -Value $icon.Value -Type DWord
            }

            # エクスプローラーの再起動
            Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
            Start-Process explorer

            return @{
                "status" = "success"
                "message" = "デスクトップアイコンの設定が完了しました"
                "icons" = $desktopIcons
            }
        }
        catch {
            throw "デスクトップアイコンの設定中にエラーが発生しました: $_"
        }
    }

    # スクリプトブロックの実行
    $remoteResult = Invoke-Command -Session $session -ScriptBlock $scriptBlock

    # 結果の設定
    $result.success = $true
    $result.message = $remoteResult.message
    $result.details = @{
        "icons" = $remoteResult.icons
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