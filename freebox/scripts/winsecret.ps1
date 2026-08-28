param(
  [Parameter(Mandatory=$true)][ValidateSet('get','set','delete')][string]$Action,
  [Parameter(Mandatory=$true)][string]$Target
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security

$dir = Join-Path $env:APPDATA 'pi-freebox-secrets'
$safe = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Target)).TrimEnd('=').Replace('+','-').Replace('/','_')
$file = Join-Path $dir "$safe.bin"
$entropy = [Text.Encoding]::UTF8.GetBytes('pi-freebox-skill-v1')

switch ($Action) {
  'get' {
    if (-not (Test-Path -LiteralPath $file)) { exit 1 }
    $protected = [IO.File]::ReadAllBytes($file)
    $bytes = [Security.Cryptography.ProtectedData]::Unprotect($protected, $entropy, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    [Console]::Out.Write([Text.Encoding]::UTF8.GetString($bytes))
  }
  'set' {
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $secret = [Console]::In.ReadToEnd()
    $bytes = [Text.Encoding]::UTF8.GetBytes($secret)
    $protected = [Security.Cryptography.ProtectedData]::Protect($bytes, $entropy, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    [IO.File]::WriteAllBytes($file, $protected)
  }
  'delete' {
    Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
  }
}
