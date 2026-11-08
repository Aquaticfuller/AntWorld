param()
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = Join-Path $project 'out/s2-performance'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$memory = @()
foreach ($name in @('antworld_s2_benchmark', 'antworld_s1_benchmark', 'antworld_scheduler_benchmark', 'antworld_benchmark')) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath "$project/build/release/$name.exe" -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$output/$name.csv" -RedirectStandardError "$output/$name.stderr.txt"
    $peakBytes = [int64]0
    while (-not $process.HasExited) {
        $process.Refresh()
        $peakBytes = [Math]::Max($peakBytes, $process.PeakWorkingSet64)
        Start-Sleep -Milliseconds 5
    }
    $process.WaitForExit()
    $watch.Stop()
    if ($process.ExitCode -ne 0) { throw "Benchmark failed: $name" }
    $memory += [pscustomobject]@{
        Benchmark = $name
        SampledPeakWorkingSetBytes = $peakBytes
        ProcessWallMs = $watch.Elapsed.TotalMilliseconds
    }
    Get-Content -LiteralPath "$output/$name.csv"
}
$memory | ConvertTo-Json | Set-Content -LiteralPath "$output/process-metrics.json" -Encoding utf8
$memory | Format-Table
