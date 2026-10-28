[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = 'Stop'
$RegistrySubKey = 'Software\Google\Chrome\NativeMessagingHosts\com.shopcontroller.chrome'
$ExpectedManifest = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'com.shopcontroller.chrome.json'))
$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($RegistrySubKey, $true)
if ($null -eq $key) {
    Write-Host '当前用户没有店铺助手登记，无需卸载。'
    return
}

$removeEmptyKey = $false
try {
    $registered = $key.GetValue('', $null)
    if (-not [string]::Equals([string]$registered, $ExpectedManifest, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Warning '当前登记属于其他安装目录。本脚本保持该登记不变。请到实际安装目录运行卸载脚本。'
        return
    }
    if ($PSCmdlet.ShouldProcess('HKCU\' + $RegistrySubKey, 'Remove the registration matching this installation only')) {
        $key.DeleteValue('', $false)
        $removeEmptyKey = $key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0
    }
}
finally { $key.Dispose() }

if ($removeEmptyKey) {
    # Delete only this now-empty key; never recursively delete a registry tree.
    [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKey($RegistrySubKey, $false)
}
Write-Host '处理完成。店铺配置、Chrome 资料、Cookie、密码和浏览器扩展均保留。'
Write-Host '若需移除扩展，请自行在各 Chrome 资料的 chrome://extensions 中移除“店铺控制器”。'
