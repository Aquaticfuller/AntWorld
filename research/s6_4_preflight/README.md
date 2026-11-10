# S6.4 Preflight scientific evidence audit

**Step 1 source inventory. Review checkpoint.** The source baseline is the accepted S6.3.4 commit `b35b988ecf1b92f7bac3c00af393b88ab8330d67`. Its `cpp` tree is `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. This inventory describes executable rules, declared values, configuration overrides and observation semantics. The paper-by-paper evidence review has its own gate.

## Inventory files

| File | Contents |
|---|---|
| [Coverage and audit report](COVERAGE_AND_AUDIT_REPORT.md) | Scope, source findings, inherited evidence and verification |
| [Current mechanism inventory](CURRENT_CORE_MECHANISM_INVENTORY.csv) | Ten biological domains plus shared execution, with source range, function, caller, enabled scope, information inputs, rule, outcome and gaps |
| [State transitions](STATE_MACHINE_TRANSITION_EVIDENCE.csv) | Entry, trigger, guards, terminal behavior, committed result and parameter references |
| [State symbol index](STATE_SYMBOL_INDEX.csv) | Source declarations for life stages, caste, motor states, task programs, scheduled kinds, outcomes and observation labels |
| [Parameter matrix](PARAMETER_EVIDENCE_MATRIX.csv) | Declared defaults and reviewed hardcoded rules with source expressions, units, scope and pending scientific evidence fields |
| [Reviewed core constants](REVIEWED_CORE_CONSTANTS.csv) | Authored source annotations for hardcoded values, formulas, gates and numerical conventions |
| [Fixture configuration index](FIXTURE_CONFIGURATION_INDEX.csv) | C++ configuration calls, initializers and overrides, including symbolic and ambiguous expressions, plus both scenario JSON sources |
| [Numeric candidate index](SOURCE_NUMERIC_CANDIDATES.csv) | Additional lexical check over Core decision sources and fixture/test sources. Matching a reviewed span identifies a candidate link. |
| [Historical crosswalk](HISTORICAL_RULE_CROSSWALK.csv) | One new source assessment for each of the 70 existing Atlas rules, with retained historical source IDs and assessments |
| [Historical anchor relocation](HISTORICAL_ANCHOR_RELOCATION.csv) | Function locations at both commits, with a check of whether the old anchor text still appears at the old line |
| [Source file coverage](SOURCE_FILE_COVERAGE.csv) | Baseline file roles, normalized file hashes and per-table primary-anchor counts |

Join on `MechanismId` and `ParameterKey`. Semicolon-delimited fields contain multiple references. A struct name refers to the whole parameter family. `CurrentSourceValue` is a source default or expression evaluated in the named context. For active settings, follow the enclosing configuration call and override expressions. Initializer omissions retain the declared defaults. Reachable states and statistics also depend on which policies the world configures and which individuals are enrolled.

`ImplementationBasis` describes the role of the current code. `MechanismEvidenceClass` remains `PENDING_FULL_TEXT_REVIEW`. The parameter matrix retains the engineering provenance of current settings separately. `ValueRoleClass` separates model settings from metadata, switches, inputs, host limits, unit conversions and execution rules. The Atlas A–F grades and historical measurements remain in their source records. A source line or a passing regression has no measured biological endpoint.

The fixture and candidate indexes are lexical. They preserve source expressions and explicitly report uncertain owner resolution. They neither perform C++ name resolution nor execute fixture call chains. Runtime values derived from a seed, branch, command-line argument, build flag or input population require the applicable frozen protocol and raw experiment. Runners and prior interpretation are linked in the report.

## Reproduce the checks

Run from the repository root with Python 3.10 or later and both commits in local Git history.

```sh
python tools/audit_s6_4_preflight.py --check
git diff --exit-code b35b988ecf1b92f7bac3c00af393b88ab8330d67 -- cpp scenarios experiments docs
```

Running the script without `--check` regenerates the six derived CSVs from the frozen source and the four authored tables. The check verifies allowed file scope, source spans, symbols, cross-references, historic rule identities and deterministic generation. Source span hashes cover UTF-8 text with LF between the named lines. Whole-file source hashes normalize line endings to LF.

[Evidence Atlas](../../ANT_BIOLOGY_EVIDENCE_ATLAS.md) · [Historical 70-rule source table](../s6_3_2_1/RULES.csv) · [Technical debt](../../docs/08_Open_Questions.md) · [Accepted storage baseline](../../S6_3_4_RESULTS.md)
