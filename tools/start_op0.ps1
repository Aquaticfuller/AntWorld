[CmdletBinding()]
param(
    [switch]$Terminal,
    [switch]$NoBrowser,
    [switch]$MicroWorld,
    [ValidateRange(1, 65535)][int]$Port = 8765,
    [string]$ImportPath,
    [string]$Cache,
    [string]$Python,
    [ValidateSet("en", "zh-CN")][string]$Language
)

$ErrorActionPreference = "Stop"
if (-not $Python) {
    foreach ($candidate in (Get-Command py, python -All -CommandType Application -ErrorAction SilentlyContinue)) {
        try {
            & $candidate.Source -B -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>$null
            if ($LASTEXITCODE -eq 0) {
                $Python = $candidate.Source
                break
            }
        } catch {
            # Ignore unavailable Windows app execution aliases.
        }
    }
}
if (-not $Python) {
    throw "Python 3.11 or later is required. Install Python, reopen PowerShell and run this script again."
}
$options = @("-B", "-X", "utf8", "-m", "op0")
if ($MicroWorld) {
    $options += "--micro"
    if (-not $Cache) { $Cache = Join-Path $PSScriptRoot "../out/m0-op0-cache" }
}
if ($Cache) {
    $options += @("--cache", $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Cache))
}
if ($Terminal) {
    $options += "tui"
    if ($Language) { $options += @("--language", $Language) }
} else {
    $options += @("serve", "--port", "$Port")
    if ($NoBrowser) { $options += "--no-browser" }
}
if ($ImportPath) {
    $options += @("--import-path", (Resolve-Path -LiteralPath $ImportPath).Path)
}

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & $Python @options
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
