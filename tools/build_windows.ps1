param(
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Debug',
    [string]$BuildDirectory = '',
    [switch]$Sanitizers
)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$toolRoot = Join-Path $project '.tools'
$compiler = Join-Path $toolRoot 'llvm-mingw-20261104-ucrt-x86_64/bin'
$cmakeBin = Join-Path $toolRoot 'cmake-3.31.10-windows-x86_64/bin'
foreach ($file in @("$compiler/clang++.exe", "$cmakeBin/cmake.exe", "$toolRoot/ninja.exe")) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Missing $file. Run tools/bootstrap_windows.ps1 first." }
}
if (-not $BuildDirectory) { $BuildDirectory = Join-Path $project "build/$($Configuration.ToLowerInvariant())" }
$oldPath = $env:PATH
try {
    $env:PATH = "$compiler;$cmakeBin;$toolRoot;$oldPath"
    & "$cmakeBin/cmake.exe" -S "$project/cpp" -B $BuildDirectory -G Ninja `
        "-DCMAKE_BUILD_TYPE=$Configuration" "-DCMAKE_CXX_COMPILER=$compiler/clang++.exe" "-DCMAKE_C_COMPILER=$compiler/clang.exe" `
        "-DCMAKE_MAKE_PROGRAM=$toolRoot/ninja.exe" "-DANTWORLD_SANITIZERS=$($Sanitizers.IsPresent)"
    if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed.' }
    & "$cmakeBin/cmake.exe" --build $BuildDirectory --parallel 4
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    & "$cmakeBin/ctest.exe" --test-dir $BuildDirectory --output-on-failure
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
} finally { $env:PATH = $oldPath }
