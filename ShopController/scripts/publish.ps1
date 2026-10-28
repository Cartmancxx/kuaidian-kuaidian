[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProductRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $ProductRoot '..'))
$DistRoot = [System.IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'dist'))
$OutputRoot = Join-Path $DistRoot 'ShopController'
$HostProject = Join-Path $ProductRoot 'host\ShopController.Host.csproj'
$ExtensionRoot = Join-Path $ProductRoot 'extension'
$BundledDotnet = Join-Path $RepositoryRoot '.tools\dotnet\dotnet.exe'
$Dotnet = if (Test-Path -LiteralPath $BundledDotnet -PathType Leaf) { $BundledDotnet } else { (Get-Command dotnet -ErrorAction Stop).Source }

function Assert-InDist([string]$Path) {
    $absolute = [System.IO.Path]::GetFullPath($Path)
    $prefix = $DistRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $absolute.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw ('输出路径超出 dist，已停止：' + $absolute)
    }
    if (Test-Path -LiteralPath $absolute) {
        $resolved = (Resolve-Path -LiteralPath $absolute).ProviderPath
        if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            ((Get-Item -LiteralPath $absolute -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw ('输出路径不是 dist 下的普通文件或目录，已停止：' + $absolute)
        }
    }
    return $absolute
}

if (-not (Test-Path -LiteralPath $DistRoot)) { New-Item -ItemType Directory -Path $DistRoot | Out-Null }
if ((Get-Item -LiteralPath $DistRoot -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw 'dist 是重解析点；请使用普通输出目录。'
}

$manifestPath = Join-Path $ExtensionRoot 'manifest.json'
$extension = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$version = [string]$extension.version
if ($version -notmatch '^\d+(\.\d+){0,3}$') { throw '扩展版本号格式无效。' }
$required = @('manifest.json', 'popup.html', 'background.js', 'manage.html', 'manage.js', 'api.js', 'style.css')
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $ExtensionRoot $relative) -PathType Leaf)) {
        throw ('扩展尚未完整：缺少 ' + $relative)
    }
}
foreach ($entry in @([string]$extension.background.service_worker, [string]$extension.options_ui.page)) {
    if ([string]::IsNullOrWhiteSpace($entry) -or [System.IO.Path]::IsPathRooted($entry) -or $entry.Contains('..') -or
        -not (Test-Path -LiteralPath (Join-Path $ExtensionRoot $entry) -PathType Leaf)) {
        throw ('扩展入口不完整或路径不合法：' + $entry)
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
$stage = Assert-InDist (Join-Path $DistRoot ('.ShopController-stage-' + $suffix))
$zipPath = Assert-InDist (Join-Path $DistRoot ('ShopController-' + $version + '-win-x64.zip'))
New-Item -ItemType Directory -Path $stage | Out-Null
Write-Host '正在生成自包含 Windows x64 本地助手…'
& $Dotnet publish $HostProject -c Release -r win-x64 --self-contained true -o (Join-Path $stage 'host') `
    -p:PublishSingleFile=true -p:PublishTrimmed=false -p:DebugType=None -p:DebugSymbols=false
if ($LASTEXITCODE -ne 0) { throw ('发布失败，暂存目录保留用于排查：' + $stage) }
if (-not (Test-Path -LiteralPath (Join-Path $stage 'host\ShopController.Host.exe') -PathType Leaf)) {
    throw '发布未生成预期的 ShopController.Host.exe。'
}

Copy-Item -LiteralPath $ExtensionRoot -Destination (Join-Path $stage 'extension') -Recurse
foreach ($script in @('Install-Host.ps1', 'Uninstall-Host.ps1', '安装本地助手.cmd', '卸载本地助手.cmd')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $script) -Destination (Join-Path $stage $script)
}
Copy-Item -LiteralPath (Join-Path $ProductRoot 'README.md') -Destination (Join-Path $stage 'README.md')
[System.IO.File]::WriteAllText((Join-Path $stage '.shopcontroller-build-output'), 'ShopController ' + $version)

# Archive an earlier output instead of deleting files. All move endpoints are checked above/below.
$OutputRoot = Assert-InDist $OutputRoot
if (Test-Path -LiteralPath $OutputRoot) {
    if (-not (Test-Path -LiteralPath (Join-Path $OutputRoot '.shopcontroller-build-output') -PathType Leaf)) {
        throw ('目标目录没有本工具的构建标记，已保持原状：' + $OutputRoot)
    }
    $backup = Assert-InDist (Join-Path $DistRoot ('ShopController.previous-' + $stamp + '-' + $suffix))
    Move-Item -LiteralPath $OutputRoot -Destination $backup
    Write-Host ('上一份输出已保留：' + $backup)
}
$stage = Assert-InDist $stage
Move-Item -LiteralPath $stage -Destination $OutputRoot
if (Test-Path -LiteralPath $zipPath) {
    $zipBackup = Assert-InDist (Join-Path $DistRoot ('ShopController-' + $version + '-win-x64.previous-' + $stamp + '-' + $suffix + '.zip'))
    Move-Item -LiteralPath $zipPath -Destination $zipBackup
}
Compress-Archive -LiteralPath $OutputRoot -DestinationPath $zipPath -CompressionLevel Optimal
$sha = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
[System.IO.File]::WriteAllText($zipPath + '.sha256', $sha + '  ' + [System.IO.Path]::GetFileName($zipPath) + [Environment]::NewLine)
Write-Host ''
Write-Host ('发布目录：' + $OutputRoot) -ForegroundColor Green
Write-Host ('ZIP：' + $zipPath) -ForegroundColor Green
Write-Host ('SHA256：' + $sha)
Write-Host '构建不会执行安装脚本，不会登记本地助手，不会安装扩展，也不会修改 Chrome 资料。'
