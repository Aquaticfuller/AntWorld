# AntWorld v0.8 design handoff

This repository begins with a complete design baseline and engineering specifications; the imported archive contained no game implementation.

## Contents

- docs/: historical design topics and v0.8 contracts, distinguishing confirmed decisions, proposals and unvalidated models.
- AGENTS.md and CODEX_START_HERE.md: repository instructions and reading order.
- codex_tasks/: stage-specific prompts; the first implementation is S0 only.
- contracts/antworld_c_api_v1.h: a later-stage ABI draft without implementation.
- schemas/ and scenarios/: machine-readable engineering fixtures, not biological calibration.
- MANIFEST_SHA256.md: hashes of the maintained English handoff files.

## Workflow

Keep this baseline in Git, read the instructions and contracts, implement one authorized stage, run its checks and report evidence. Review S0_RESULTS.md before deciding whether to proceed to S1. Keep earlier designs as historical context; later confirmed decisions take precedence.

## Unfinished research and implementation

The baseline did not include executed ant behavior, Unity or GM tests. Species calibration, SDF primitives and numerical accuracy, Agent harness selection, and multi-precision performance remain research or development work. Do not report them as completed merely because their contracts exist.

## English repository policy

On 2026-11-08, the user required English for every tracked file, code comment, document and commit message. The original Chinese archive remains in the local ignored handoff/ directory and in the pre-policy historical commit; it is no longer tracked at the branch tip. Existing Git history is preserved. README_HANDOFF_CN.md was renamed to this file. Translations retain the design decisions and historical status; implementation-specific clarifications belong in separate ADRs.
