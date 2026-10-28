[CmdletBinding()]
param(
    [ValidateSet('store', 'github')][string]$Channel = 'store',
    [string]$ExtensionId = '',
    [string]$Dotnet = '',
    [string]$Python = '',
    [switch]$SkipBuild,
    [switch]$BuildOnly,
    [switch]$RequirePublishReady
)
$ErrorActionPreference = 'Stop'
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$arguments = @((Join-Path $PSScriptRoot 'publish_release.py'))
$arguments += @('--channel', $Channel)
if ($ExtensionId) { $arguments += @('--extension-id', $ExtensionId) }
if ($Dotnet) { $arguments += @('--dotnet', $Dotnet) }
if ($SkipBuild) { $arguments += '--skip-build' }
if ($BuildOnly) { $arguments += '--build-only' }
if ($RequirePublishReady) { $arguments += '--require-publish-ready' }
& $Python @arguments
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed. Staging files were retained for diagnostics.' }
