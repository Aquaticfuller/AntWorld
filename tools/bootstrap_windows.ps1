param([string]$Destination = (Join-Path $PSScriptRoot '../.tools'))
$ErrorActionPreference = 'Stop'
$Destination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$packages = @(
    @{
        Name = 'llvm-mingw-20261104-ucrt-x86_64'
        Url = 'https://github.com/mstorsjo/llvm-mingw/releases/download/20261104/llvm-mingw-20261104-ucrt-x86_64.zip'
        Sha256 = '552191b5754c49a5a20723276a6fc56541ea1922c4c50b7b669022333fc1b40f'
        Probe = 'llvm-mingw-20261104-ucrt-x86_64/bin/clang++.exe'
    },
    @{
        Name = 'cmake-3.31.10-windows-x86_64'
        Url = 'https://github.com/Kitware/CMake/releases/download/v3.31.10/cmake-3.31.10-windows-x86_64.zip'
        Sha256 = '13d1a463d7130df5339baedd63d8ae990aaf385062b2f42f372796143ae94086'
        Probe = 'cmake-3.31.10-windows-x86_64/bin/cmake.exe'
    },
    @{
        Name = 'ninja-1.13.2'
        Url = 'https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip'
        Sha256 = '07fc8261b42b20e71d1720b39068c2e14ffcee6396b76fb7a795fb460b78dc65'
        Probe = 'ninja.exe'
    }
)
foreach ($package in $packages) {
    if (Test-Path -LiteralPath (Join-Path $Destination $package.Probe)) {
        Write-Output "Already available: $($package.Name)"
        continue
    }
    $archive = Join-Path $Destination ($package.Name + '.zip')
    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Output "Downloading $($package.Name)"
        Invoke-WebRequest -Uri $package.Url -OutFile $archive
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $package.Sha256) {
        throw "SHA-256 mismatch: $archive. Remove this archive before retrying."
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $Destination -Force
    if (-not (Test-Path -LiteralPath (Join-Path $Destination $package.Probe))) {
        throw "Missing executable after extraction: $($package.Probe)"
    }
    Write-Output "Verified and extracted $($package.Name)"
}
Write-Output 'Toolchain ready. Run tools/build_windows.ps1 to build and test.'
