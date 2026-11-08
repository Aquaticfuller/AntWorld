param()
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = Join-Path $project 'out/s1-performance'
$baseline = Join-Path $output 's0-source'
$compiler = Join-Path $project '.tools/llvm-mingw-20261104-ucrt-x86_64/bin/clang++.exe'
New-Item -ItemType Directory -Path $baseline -Force | Out-Null
Push-Location $project
try {
    # Export the immutable reviewed S0 commit without changing the working branch.
    & git archive --format=tar "--output=$output/s0-source.tar" 548df2d2d76a0c3c505669f11af0199fec02ae83 cpp
    if ($LASTEXITCODE -ne 0) { throw 'Cannot export reviewed S0 sources.' }
    & tar -xf "$output/s0-source.tar" -C $baseline
    if ($LASTEXITCODE -ne 0) { throw 'Cannot extract baseline sources.' }
    & $compiler -std=c++20 -O3 -DNDEBUG -static "-I$baseline/cpp/include" `
        cpp/apps/antworld_scheduler_benchmark.cpp "$baseline/cpp/src/world_runtime.cpp" `
        "$baseline/cpp/src/types.cpp" -o "$output/s0_scheduler_benchmark.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot build baseline scheduler benchmark.' }
    $jobs = @(
        @{ Name = 's0-scheduler'; Executable = "$output/s0_scheduler_benchmark.exe" },
        @{ Name = 's1-scheduler'; Executable = "$project/build/release/antworld_scheduler_benchmark.exe" },
        @{ Name = 's1-entities'; Executable = "$project/build/release/antworld_s1_benchmark.exe" },
        @{ Name = 's1-diagnostics'; Executable = "$project/build/release/antworld_benchmark.exe" }
    )
    $memory = @()
    foreach ($job in $jobs) {
        $watch = [Diagnostics.Stopwatch]::StartNew()
        $process = Start-Process -FilePath $job.Executable -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput "$output/$($job.Name).txt" -RedirectStandardError "$output/$($job.Name).stderr.txt"
        $peakBytes = [int64]0
        while (-not $process.HasExited) {
            $process.Refresh()
            $peakBytes = [Math]::Max($peakBytes, $process.PeakWorkingSet64)
            Start-Sleep -Milliseconds 5
        }
        $process.WaitForExit()
        $watch.Stop()
        if ($process.ExitCode -ne 0) { throw "Benchmark failed: $($job.Name)" }
        $memory += [pscustomobject]@{
            Benchmark = $job.Name
            SampledPeakWorkingSetBytes = $peakBytes
            ProcessWallMs = $watch.Elapsed.TotalMilliseconds
        }
        Get-Content -LiteralPath "$output/$($job.Name).txt"
    }
    $memory | ConvertTo-Json | Set-Content -LiteralPath "$output/process-metrics.json" -Encoding utf8
    $memory | Format-Table
} finally { Pop-Location }
