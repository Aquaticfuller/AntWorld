param([string]$OutputDirectory = 'out/s3-performance')
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = Join-Path $project $OutputDirectory
& "$PSScriptRoot/benchmark_s2_windows.ps1" -OutputDirectory "$OutputDirectory/s2"
New-Item -ItemType Directory -Path $output -Force | Out-Null
$watch = [Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath "$project/build/release/antworld_s3_benchmark.exe" -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$output/physiology.csv" -RedirectStandardError "$output/physiology.stderr.txt"
$peakBytes = [int64]0
while (-not $process.HasExited) {
    $process.Refresh()
    $peakBytes = [Math]::Max($peakBytes, $process.PeakWorkingSet64)
    Start-Sleep -Milliseconds 5
}
$process.WaitForExit()
$watch.Stop()
if ($process.ExitCode -ne 0) { throw 'S3 benchmark failed' }
[pscustomobject]@{ Benchmark = 'antworld_s3_benchmark'; SampledPeakWorkingSetBytes = $peakBytes; ProcessWallMs = $watch.Elapsed.TotalMilliseconds } |
    ConvertTo-Json | Set-Content -LiteralPath "$output/process-metrics.json" -Encoding utf8
Get-Content -LiteralPath "$output/physiology.csv"
