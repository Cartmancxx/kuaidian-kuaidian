[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$ExtensionId = '', [switch]$ReplaceIdentity)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Version.Build -lt 22000) { throw 'This release supports Windows 11 x64 in a currently supported servicing release.' }
$HostName = 'com.shopcontroller.chrome'
$RegistryPath = 'Software\Google\Chrome\NativeMessagingHosts\' + $HostName
$LocalRoot = [IO.Path]::GetFullPath([Environment]::GetFolderPath('LocalApplicationData'))
$Programs = Join-Path $LocalRoot 'Programs'
$Target = [IO.Path]::GetFullPath((Join-Path $Programs 'ShopController'))
$Source = [IO.Path]::GetFullPath($PSScriptRoot)
$ManifestPath = Join-Path $Target ($HostName + '.json')
$Utf8 = New-Object Text.UTF8Encoding($false)

function Assert-NoRedirect([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw ('Redirected path is not accepted: ' + $current)
            }
        }
        $parent = [IO.Path]::GetDirectoryName($current)
        if ($parent -eq $current) { break }
        $current = $parent
    }
}
function Assert-ProductPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $Programs.TrimEnd('\') + '\ShopController'
    if (-not ($full -eq $prefix -or $full.StartsWith($prefix + '.', [StringComparison]::OrdinalIgnoreCase))) {
        throw ('Unexpected installation target: ' + $full)
    }
    Assert-NoRedirect $full
    return $full
}

$mutexName = 'Local\ShopControllerInstall_' + [Security.Principal.WindowsIdentity]::GetCurrent().User.Value.Replace('-', '_')
$installMutex = New-Object System.Threading.Mutex($false, $mutexName)
$installLockHeld = $false
try {
    try { $installLockHeld = $installMutex.WaitOne(30000) }
    catch [System.Threading.AbandonedMutexException] { $installLockHeld = $true }
    if (-not $installLockHeld) { throw 'Another ShopController install or uninstall is running. Try again after it finishes.' }
Assert-NoRedirect $Source
Assert-NoRedirect $Target
if ($Source.Equals($Target, [StringComparison]::OrdinalIgnoreCase)) { throw 'Run Install.ps1 from the newly extracted download, not the installed folder.' }
$Metadata = Get-Content -LiteralPath (Join-Path $Source 'release-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Metadata.product -ne 'ShopController' -or $Metadata.runtime -ne 'win-x64' -or $Metadata.version -notmatch '^\d+(\.\d+){1,3}$') {
    throw 'This package is not a valid Windows x64 ShopController release.'
}
if ($Metadata.extensionId) {
    if ($ExtensionId -and $ExtensionId -cne $Metadata.extensionId) { throw 'This package is bound to a different extension ID.' }
    $ExtensionId = [string]$Metadata.extensionId
}
if (-not $ExtensionId) { $ExtensionId = (Read-Host 'Paste the actual Shop Controller ID shown in chrome://extensions').Trim() }
if ($ExtensionId -cnotmatch '^[a-p]{32}$') { throw 'The extension ID must contain exactly 32 lowercase letters a-p.' }
if (-not (Test-Path -LiteralPath (Join-Path $Source 'host\ShopController.Host.exe') -PathType Leaf)) { throw 'The host executable is missing. Extract the complete package first.' }
Get-ChildItem -LiteralPath (Join-Path $Source 'host') -Recurse -Force | ForEach-Object {
    if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw ('Package contains a redirected item: ' + $_.FullName) }
}
if (Test-Path -LiteralPath $Target) {
    if (-not (Test-Path -LiteralPath (Join-Path $Target '.shopcontroller-install') -PathType Leaf)) { throw 'The target already exists without a ShopController installation marker. It has been preserved.' }
    $identityPath = Join-Path $Target 'host\host-identity.json'
    if (Test-Path -LiteralPath $identityPath) {
        $oldIdentity = Get-Content -LiteralPath $identityPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($oldIdentity.extensionId -cne $ExtensionId -and -not $ReplaceIdentity) { throw 'The installed helper is bound to another extension. Re-run with -ReplaceIdentity only after confirming migration.' }
    }
}
$oldValue = $null
$readKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($RegistryPath, $false)
if ($readKey) { try { $oldValue = $readKey.GetValue('', $null) } finally { $readKey.Dispose() } }
if ($oldValue -and -not [string]::Equals([string]$oldValue, $ManifestPath, [StringComparison]::OrdinalIgnoreCase)) {
    throw ('Another helper location is registered. Uninstall its registration first: ' + $oldValue)
}
if (-not $PSCmdlet.ShouldProcess($Target, 'Install the per-user helper and register its exact extension ID')) { return }

New-Item -ItemType Directory -Force -Path $Programs | Out-Null
$suffix = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 6)
$stage = Assert-ProductPath ($Target + '.stage-' + $suffix)
$backup = Assert-ProductPath ($Target + '.previous-' + $suffix)
$failed = Assert-ProductPath ($Target + '.failed-' + $suffix)
$movedOld = $false
$movedNew = $false
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    Copy-Item -LiteralPath (Join-Path $Source 'host') -Destination (Join-Path $stage 'host') -Recurse
    Copy-Item -LiteralPath (Join-Path $Source 'runtime-notices') -Destination (Join-Path $stage 'runtime-notices') -Recurse
    foreach ($file in @('release-config.json', 'Uninstall.ps1', 'Uninstall.cmd', 'README.txt')) {
        Copy-Item -LiteralPath (Join-Path $Source $file) -Destination (Join-Path $stage $file)
    }
    [IO.File]::WriteAllText((Join-Path $stage '.shopcontroller-install'), 'ShopController ' + $Metadata.version, $Utf8)
    [IO.File]::WriteAllText((Join-Path $stage 'host\host-identity.json'), (@{ extensionId = $ExtensionId } | ConvertTo-Json), $Utf8)
    $manifest = [ordered]@{ name = $HostName; description = 'Shop Controller native profile launcher'; path = (Join-Path $Target 'host\ShopController.Host.exe'); type = 'stdio'; allowed_origins = @('chrome-extension://' + $ExtensionId + '/') }
    [IO.File]::WriteAllText((Join-Path $stage ($HostName + '.json')), ($manifest | ConvertTo-Json -Depth 4), $Utf8)
    if (Test-Path -LiteralPath $Target) {
        $null = Assert-ProductPath $Target
        Move-Item -LiteralPath $Target -Destination $backup
        $movedOld = $true
    }
    $null = Assert-ProductPath $stage
    Move-Item -LiteralPath $stage -Destination $Target
    $movedNew = $true
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($RegistryPath)
    try { $key.SetValue('', $ManifestPath, [Microsoft.Win32.RegistryValueKind]::String) } finally { $key.Dispose() }
    Write-Host ('Installed helper ' + $Metadata.version + ': ' + $Target) -ForegroundColor Green
    Write-Host ('Allowed extension ID: ' + $ExtensionId)
    Write-Host 'Return to the Chrome extension and choose Retry. No Chrome profile, Cookie, or password was changed.'
    if ($movedOld) { Write-Host ('Previous files preserved for rollback: ' + $backup) }
}
catch {
    $original = $_
    if ($movedNew -and (Test-Path -LiteralPath $Target)) {
        $null = Assert-ProductPath $Target
        Move-Item -LiteralPath $Target -Destination $failed
    }
    if ($movedOld -and (Test-Path -LiteralPath $backup)) {
        $null = Assert-ProductPath $backup
        Move-Item -LiteralPath $backup -Destination $Target
    }
    if ($movedNew) {
        $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($RegistryPath)
        try { if ($oldValue) { $key.SetValue('', $oldValue) } else { $key.DeleteValue('', $false) } } finally { $key.Dispose() }
    }
    throw $original
}

}
finally {
    if ($installLockHeld) { $installMutex.ReleaseMutex() }
    $installMutex.Dispose()
}
