[CmdletBinding()]
param(
    [switch]$Terminal,
    [switch]$NoBrowser,
    [ValidateRange(1, 65535)][int]$Port = 8765,
    [string]$ImportPath,
    [string]$Cache,
    [string]$Python
)

$ErrorActionPreference = "Stop"
if (-not $Python) {
    foreach ($candidate in @("py", "python")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            & $candidate -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>$null
            if ($LASTEXITCODE -eq 0) {
                $Python = $candidate
                break
            }
        }
    }
}
if (-not $Python) {
    throw "Python 3.11 or later is required. Install Python, reopen PowerShell and run this script again."
}
$options = @("-X", "utf8", "-m", "op0")
if ($Cache) {
    $options += @("--cache", $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Cache))
}
if ($Terminal) {
    $options += "tui"
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
