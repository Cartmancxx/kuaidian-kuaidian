[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$ReplaceExisting)

$ErrorActionPreference = 'Stop'
$HostName = 'com.shopcontroller.chrome'
$ExtensionId = 'hadeebhijljjdebkaiaglaeipajnnind'
$RegistrySubKey = 'Software\Google\Chrome\NativeMessagingHosts\' + $HostName
$PackageRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$HostExe = Join-Path $PackageRoot 'host\ShopController.Host.exe'
$ExtensionManifest = Join-Path $PackageRoot 'extension\manifest.json'
$NativeManifest = Join-Path $PackageRoot 'com.shopcontroller.chrome.json'

if (-not (Test-Path -LiteralPath $HostExe -PathType Leaf)) {
    throw '找不到 host\ShopController.Host.exe。请先解压完整发布包，再从发布包根目录安装。'
}
if (-not (Test-Path -LiteralPath $ExtensionManifest -PathType Leaf)) {
    throw '找不到 extension\manifest.json。请保留发布包完整目录结构。'
}

$extension = Get-Content -LiteralPath $ExtensionManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $extension.key) { throw '扩展清单缺少固定公钥；没有修改系统登记。' }
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try { $hash = $sha256.ComputeHash([Convert]::FromBase64String([string]$extension.key)) }
finally { $sha256.Dispose() }
$calculatedId = -join (0..15 | ForEach-Object {
    [char](97 + ($hash[$_] -shr 4))
    [char](97 + ($hash[$_] -band 15))
})
if ($calculatedId -cne $ExtensionId) {
    throw '扩展 ID 与此安装器不匹配；没有修改系统登记。请使用同一发布包中的扩展和助手。'
}

$registered = $null
$readKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($RegistrySubKey, $false)
if ($null -ne $readKey) {
    try { $registered = $readKey.GetValue('', $null) }
    finally { $readKey.Dispose() }
}
if ($registered -and -not [string]::Equals([string]$registered, $NativeManifest, [StringComparison]::OrdinalIgnoreCase) -and -not $ReplaceExisting) {
    throw ('已有另一个目录的店铺助手登记：' + $registered + [Environment]::NewLine +
        '请先在旧目录运行 Uninstall-Host.ps1，或确认迁移后使用 Install-Host.ps1 -ReplaceExisting。店铺配置会保留。')
}

$manifest = [ordered]@{
    name = $HostName
    description = 'Shop Controller native Chrome profile launcher'
    path = [System.IO.Path]::GetFullPath($HostExe)
    type = 'stdio'
    allowed_origins = @('chrome-extension://' + $ExtensionId + '/')
}

if ($PSCmdlet.ShouldProcess($NativeManifest, 'Create native messaging manifest and register this helper for the current Windows user')) {
    $json = $manifest | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($NativeManifest, $json, (New-Object System.Text.UTF8Encoding($false)))
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($RegistrySubKey)
    try { $key.SetValue('', $NativeManifest, [Microsoft.Win32.RegistryValueKind]::String) }
    finally { $key.Dispose() }

    Write-Host ''
    Write-Host '本地助手已登记，仅对当前 Windows 用户生效。' -ForegroundColor Green
    Write-Host ('发布目录：' + $PackageRoot)
    Write-Host ('扩展目录：' + (Join-Path $PackageRoot 'extension'))
    Write-Host ''
    Write-Host '下一步：在 Chrome 打开 chrome://extensions，开启开发者模式，点击“加载已解压的扩展程序”，选择上面的 extension 目录。'
    Write-Host '随后核对扩展 ID：hadeebhijljjdebkaiaglaeipajnnind。'
    Write-Host '请保留整个发布目录，不要放在临时目录，也不要安装后移动或删除。'
    Write-Host '本安装器没有自动安装 Chrome 扩展，没有修改 Chrome 资料、Cookie 或密码。'
}
