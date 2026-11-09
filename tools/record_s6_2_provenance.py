"""Bind frozen S6.2 measurements to actual binaries, compiler and unchanged Core trees."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    normal = json.loads((ROOT/'experiments/s6_2/performance/primary/configuration.json').read_text())
    profile = json.loads((ROOT/'experiments/s6_2/performance/attribution/configuration.json').read_text())
    assert digest(ROOT/'build/s6_2-release/antworld_s6_2_benchmark.exe') == normal['binary_sha256']
    assert digest(ROOT/'build/s6_2-profile/antworld_s6_2_benchmark.exe') == profile['binary_sha256']
    trees = {}
    for name in ('cpp/src', 'cpp/include'):
        baseline, current = git('rev-parse', f'4a4827c:{name}'), git('rev-parse', f'HEAD:{name}')
        assert baseline == current
        trees[name] = current
    old_changes = git('diff', '--name-only', '4a4827c', '--', 'experiments')
    assert all(line.startswith('experiments/s6_2/') for line in old_changes.splitlines())
    compiler = ROOT/'.tools/llvm-mingw-20261104-ucrt-x86_64/bin/clang++.exe'
    version = subprocess.check_output([str(compiler), '--version'], text=True).splitlines()[:3]
    flags = {}
    for tag in ('release', 'profile'):
        cache = (ROOT/f'build/s6_2-{tag}/CMakeCache.txt').read_text(encoding='utf-8')
        flags[tag] = [line for line in cache.splitlines() if line.startswith((
            'CMAKE_BUILD_TYPE:', 'CMAKE_CXX_FLAGS:', 'CMAKE_CXX_FLAGS_RELEASE:',
            'ANTWORLD_PROFILE:', 'ANTWORLD_SANITIZERS:', 'ANTWORLD_STORAGE:'))]
    result = dict(baseline_commit=git('rev-parse', '4a4827c'), protocol_commit=git('rev-parse', '3f6d1a9'),
                  benchmark_source_commit=normal['source_commit'], observer_source_commit=git('rev-parse', '95bbc5a'),
                  unchanged_core_trees=trees, all_prior_experiment_files_unchanged=True,
                  compiler=version, compiler_binary_sha256=digest(compiler), configurations=flags,
                  binary_sha256=dict(benchmark=normal['binary_sha256'], profile=profile['binary_sha256'],
                    nutrition=digest(ROOT/'build/s6_2-release/antworld_s6_2_nutrition.exe'),
                    choice=digest(ROOT/'build/s6_2-release/antworld_s6_2_choice.exe')),
                  choice=dict(scope='ENGINEERING_FIXTURE', seeds=list(range(1, 65)), permutations=4,
                              cases=256, larvae=16, donor_initial_protein_ug=1000, transfer_limit_ug=1,
                              decisions_per_case=64, spacing_m=.0002, contact_radius_m=.002,
                              gift_first=True, local_work_continuation=True, encounter_budget=16,
                              autonomy=False, recipient_requirement_ug=100, schema=8, physics=9),
                  scope='No biological defaults, Core behavior, scheduling, RNG, contact frequency or facts changed.')
    (ROOT/'experiments/s6_2/provenance.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('PASS actual measured binaries, compiler and unchanged Core/history provenance')


if __name__ == '__main__':
    main()
