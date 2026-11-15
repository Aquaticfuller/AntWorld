"""Build just the MicroWorld live executable with the available toolchain."""

from argparse import ArgumentParser
import os
from pathlib import Path
from shutil import copyfile
import subprocess
from tempfile import TemporaryDirectory


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    root = Path(__file__).resolve().parent.parent
    build = root / "build/m0-live"
    output = root / "out/m0-live-bin"
    output.mkdir(parents=True, exist_ok=True)
    cmake = "cmake"
    config = ["-DCMAKE_BUILD_TYPE=Release"]
    if os.name == "nt":
        tools = root / ".tools"
        portable = tools / "cmake-3.31.10-windows-x86_64/bin/cmake.exe"
        compiler = tools / "llvm-mingw-20261104-ucrt-x86_64/bin"
        ninja = tools / "ninja.exe"
        if all(path.is_file() for path in (portable, compiler / "clang.exe", compiler / "clang++.exe", ninja)):
            cmake = str(portable)
            config.extend(["-G", "Ninja", f"-DCMAKE_C_COMPILER={(compiler/'clang.exe').as_posix()}",
                           f"-DCMAKE_CXX_COMPILER={(compiler/'clang++.exe').as_posix()}",
                           f"-DCMAKE_MAKE_PROGRAM={ninja.as_posix()}"])
    with TemporaryDirectory(dir=output.parent, prefix="m0-build-") as temp:
        env = os.environ | {"TMPDIR": temp, "TEMP": temp, "TMP": temp}
        subprocess.run([cmake, "-S", str(root / "cpp"), "-B", str(build), *config], check=True, env=env)
        subprocess.run([cmake, "--build", str(build), "--config", "Release", "--target", "antworld_m0_live",
                        "--parallel", str(args.jobs)], check=True, env=env)
        name = "antworld_m0_live.exe" if os.name == "nt" else "antworld_m0_live"
        source = build / "Release" / name
        if not source.is_file():
            source = build / name
        stage = Path(temp) / name
        copyfile(source, stage)
        stage.chmod(source.stat().st_mode)
        installed = (output / name).with_stem("antworld_m0_live_v3")
        stage.replace(installed)
    print(installed)


if __name__ == "__main__":
    main()
