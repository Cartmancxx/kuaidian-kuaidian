[CmdletBinding(SupportsShouldProcess = $true)]
param()
$ErrorActionPreference = 'Stop'
$Programs = [IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs'))
$Target = Join-Path $Programs 'ShopController'
$Manifest = Join-Path $Target 'com.shopcontroller.chrome.json'
$RegistryPath = 'Software\Google\Chrome\NativeMessagingHosts\com.shopcontroller.chrome'
$mutexName = 'Local\ShopControllerInstall_' + [Security.Principal.WindowsIdentity]::GetCurrent().User.Value.Replace('-', '_')
$installMutex = New-Object System.Threading.Mutex($false, $mutexName)
$installLockHeld = $false
try {
    try { $installLockHeld = $installMutex.WaitOne(30000) }
    catch [System.Threading.AbandonedMutexException] { $installLockHeld = $true }
    if (-not $installLockHeld) { throw 'Another ShopController install or uninstall is running. Try again after it finishes.' }
$current = $Target
while ($current) {
    if ((Test-Path -LiteralPath $current) -and ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw ('Redirected path preserved: ' + $current) }
    $current = [IO.Path]::GetDirectoryName($current)
}
if ((Test-Path -LiteralPath $Target) -and -not (Test-Path -LiteralPath (Join-Path $Target '.shopcontroller-install') -PathType Leaf)) { throw 'Target has no ShopController marker; no files or registration changed.' }
$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($RegistryPath, $true)
$deleteKey = $false
if ($key) {
    try {
        $value = $key.GetValue('', $null)
        if ($value -and -not [string]::Equals([string]$value, $Manifest, [StringComparison]::OrdinalIgnoreCase)) { throw ('Registration points to another installation; preserved: ' + $value) }
        if ($PSCmdlet.ShouldProcess($Manifest, 'Remove only this helper registration')) {
            $key.DeleteValue('', $false)
            $deleteKey = $key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0
        }
    } finally { $key.Dispose() }
}
if ($deleteKey) { [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKey($RegistryPath, $false) }
if ((Test-Path -LiteralPath $Target) -and $PSCmdlet.ShouldProcess($Target, 'Archive installed binaries; keep user configuration')) {
    $archive = [IO.Path]::GetFullPath($Target + '.uninstalled-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6))
    if (-not $archive.StartsWith($Programs.TrimEnd('\') + '\ShopController.uninstalled-', [StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $archive)) { throw 'Unexpected archive target; files preserved.' }
    Move-Item -LiteralPath $Target -Destination $archive
    Write-Host ('Installed files archived for recovery: ' + $archive)
}
Write-Host 'Helper registration removed. Shop configuration, Chrome data, and the extension remain unchanged.'

}
finally {
    if ($installLockHeld) { $installMutex.ReleaseMutex() }
    $installMutex.Dispose()
}
