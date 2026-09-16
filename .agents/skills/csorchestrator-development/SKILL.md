---
name: csorchestrator-development
description: >-
  Develops, audits, and maintains the csorchestrator framework.
  Use when understanding the layered architecture, adding or changing steps, recipes,
  or CLI commands, validating layer/import contracts, running tests and pre-commit
  quality gates, or re-generating GitHub Actions workflows and the portable SDK that
  gets copied into client projects.
---

# csorchestrator Framework Development

## Overview

csorchestrator is a Python framework used by client projects (e.g. `3rdPartyBaseLibs`, `csQt6`)
to define cross-platform C/C++ (CMake) build pipelines. A *project script* (e.g. `3rdPartyBaseLibs.py`,
`qt6.py`) exposes a `create_orchestrator() -> OptionalResultWithReport[Orchestrator]` function that builds
an `Orchestrator` object — phases made of steps, plus an execution matrix (OS × arch × compiler/generator)
and a workflow config. The framework then:

- **validates** the orchestrator,
- **executes** it locally, or
- **translates** it into a GitHub Actions workflow (matrix job + optional release-on-tag job), and
- packages **release artifacts** (archives) with a self-contained **portable SDK** (`csorchestratorsdk`)
  and a **release manifest** (`*.csOrchestratorManifest` JSON) that client projects consume/download.

## Dependencies

- **Python**: `>= 3.11` in the active `.venv` (created by `./setup.sh`)
- **Runtime**: `click`, `PyYAML`, `GitPython`, `colorama`
- **Dev**: `pytest`, `pytest-cov`, `mypy` (strict), `ruff`, `pre-commit`, `import-linter`
- **Network**: `git`-marked tests access `github.com/cscosine/csorchestratorTestRepo`
  (token secret `ACTIONS_ORG_ACCESS`); see `tests/csorchestrator/repo_test_data_config.py`

## Quick Start

```bash
./setup.sh                       # one-time: venv + deps + pre-commit hooks
pytest                           # fast subset (slow/git tests are skipped by default)
pytest --run-all                 # full suite, including slow and git-dependent tests
pre-commit run --all-files       # quality gate (ruff, mypy, import-linter, ...)
```

## Workflow

Follow these steps when interacting with or modifying the csorchestrator framework.

### 1. Understand the Layered Architecture (Fail-Loud Import Contract)

The package is organized in strict layers, enforced by `import-linter` contracts in
[`pyproject.toml`](pyproject.toml)
(`[tool.importlinter]`). Higher layers may import lower layers, never the reverse.

| Layer | Role | Landmark files |
|---|---|---|
| `application` | CLI, recipes, factory (user-facing) | `application/cli/cli.py`, `application/recipes/*.py`, `application/factory/factory.py` |
| `frontend` | features of an Orchestrator: steps, validation, local execution, GitHub wf translation, reporters | `frontend/step/`, `frontend/validation/`, `frontend/local_execution/`, `frontend/github_workflow_translation/`, `frontend/cscmake_presets/` |
| `domain` | pure domain model (no I/O): Orchestrator, Phase, steps, contexts, execution | `domain/orchestrator/`, `domain/context/`, `domain/execution/` |
| `foundation` | generic building blocks, no domain dependency | `foundation/core/` (Report, Expected), `foundation/git/`, `foundation/file_system/` |
| `portable` | self-contained SDK copied into client projects | `portable/package_version.py`, `portable/release_manifest.py` |

> [!WARNING]
> `domain` and `foundation` must stay pure (no `click`/`yaml`/filesystem side effects unless present in
> foundation's own helpers). If `lint-imports` fails, fix the import location — do not silence or work
> around the contract.

### 2. Map the Code Before Editing

- [`application/cli/cli.py`](src/csorchestrator/application/cli/cli.py):
  click group with global `--sink {print,colored,colorama,none}` and `--markdown PATH`; commands
  `run`, `describe`, and `generate-github-workflow`. `orchestrator_main_with_default_run()` makes a project script
  behave like the CLI entry point (no args → `run`). Console script is `csorchestrator`.
- [`application/recipes/create_orchestrator.py`](src/csorchestrator/application/recipes/create_orchestrator.py):
  `create_default_orchestrator()` (name, version, install dir, matrix, workflow trigger/release config)
  and `create_default_execution_matrix()`.
- [`application/recipes/checkout_build.py`](src/csorchestrator/application/recipes/checkout_build.py):
  `checkout_repos()`, `build_repos()`, `create_and_upload_artifacts()`, `checkout_build_and_archive_repos()`.
- [`application/recipes/manifest_github.py`](src/csorchestrator/application/recipes/manifest_github.py):
  `download_manifest()` for clients.
- [`domain/orchestrator/orchestrator.py`](src/csorchestrator/domain/orchestrator/orchestrator.py):
  `Orchestrator` (name/version/execution_matrix/phases/wf_config), `create_phase()`.
- [`domain/orchestrator/step_base.py`](src/csorchestrator/domain/orchestrator/step_base.py):
  `StepBase` with `add_extra()`/`add_capability()`.
- [`frontend/step/`](src/csorchestrator/frontend/step/):
  concrete steps (`StepGetRepositoryGitHub`, `StepCMakeWorkflow`, `StepCustomCommand`/`StepBashScriptCommand`/
  `StepWinPSCommand`, `StepCreateArchives`, `StepUploadArtifacts`,
  `StepGetVersionsFromCMakeConfigPackageVersion`, `StepAddGitHubAction`, ...).
- [`portable/`](src/csorchestrator/portable/):
  `PackageVersion`, `ReleaseManifest`, version grep utilities — copied verbatim into client projects.

### 3. How Steps Work (Capabilities Pattern)

A step subclasses `StepBase` and registers **capabilities** in `__post_init__` via `add_capability`:

- `StepCapabilityLocalExecution` (`frontend/local_execution/orchestrator_visitor_local_executor.py`):
  implements `execute_locally(context, reporter_sink) -> Report` for local `run`.
- `StepCapabilityGithubWorkflow` (`frontend/github_workflow_translation/orchestrator_visitor_github_wf_generator.py`):
  implements `to_githubwf(...)` (and optionally `to_githubwf_setup`/`to_githubwf_post`).

Blueprint used by existing steps: an ABC companion class declaring the capability method as abstract,
a concrete capability class, and the `StepBase` subclass registering it. Inspect
[`step_custom_command.py`](src/csorchestrator/frontend/step/step_custom_command.py)
as a reference before adding a new step.

### 4. Portable Code & Generated Workflows

- Code that must run **inside generated GitHub Actions jobs** lives in `portable/` and is embedded from
  templates in
  [`frontend/step/templates/`](src/csorchestrator/frontend/step/templates/).
- When such code is embedded, `relocate_portable_imports()` (in `frontend/step/templates/utils.py`)
  rewrites `from csorchestrator.portable...` → `from csorchestratorsdk.portable...`, because the portable
  folder is copied into client projects as `csorchestratorsdk/portable`.
- `generate-github-workflow` (without `-o`) also re-copies the SDK via `copy_portable_csorchestrator()`
  into the project script folder — see
  [`validate_and_generate_github_workflow.py`](src/csorchestrator/frontend/github_workflow_translation/validate_and_generate_github_workflow.py).
  With `-o <file>` the workflow is written to the exact file and the SDK is **not** copied.

### 5. Running the Tests

- pytest config lives in `pyproject.toml` (`[tool.pytest.ini_options]`); markers: `slow`, `git`, `requires`.
  `conftest.py` adds `--run-all`, `--run-slow`, `--run-git`, `--requires-mandatory`.
- Slow/git tests are **skipped by default** — do not report them as failures.
- The `git` tests need the `csorchestratorTestRepo` fixture; if clone/checkout behavior changes, regenerate
  the fixture with `tools/regenerate_test_repo.py` and update `initial_commit_sha` in
  `tests/csorchestrator/repo_test_data_config.py`.

### 6. Quality Gate

Before concluding any change:

```bash
pre-commit run --all-files
```

- Hooks: ruff (autofix) + ruff-format, mypy (strict), actionlint, `lint-imports`, VS Code launch
  regeneration, and a final `git diff --quiet` (fail if unstaged changes remain).
- `.vscode/launch.json` is **auto-generated** by `tools/generate_vscode_launch.py`; never edit it by hand.

### 7. Documentation Synchronization

When the package layout, CLI, or recipe API changes, update
[`README.md`](README.md) — repository structure, package
structure, and "Using the package" CLI/library examples must stay accurate.

## Rate Limiting

- **Do not run full local executions** (`run`) of real client recipes (e.g. `3rdPartyBaseLibs.py`,
  `qt6.py`) inside the agent environment: they need network access, the `ACTIONS_ORG_ACCESS` token,
  compiler toolchains, and can take hours. Prefer `pytest` unit tests or `generate-github-workflow` runs.
- `git`-marked tests require network access to GitHub; skip them unless connectivity plus the
  `ACTIONS_ORG_ACCESS` secret are available.
- Do not mutate `.venv`, `.mypy_cache`, `.ruff_cache`, or other caches by hand.

## Common Mistakes

1. **Layer violation**: importing `frontend` from `domain`/`foundation` — `import-linter` fails. Place new
   generic logic in `foundation`, domain logic in `domain`, and only features/visitors in `frontend`.
2. **Editing autogenerated artifacts**: `csorchestratorsdk/portable` in client projects, `.vscode/launch.json`,
   or workflow YAML files generated from recipes. Regenerate instead.
3. **Treating skipped tests as failures**: slow/git tests are intentionally skipped without `--run-all`;
   use `pytest --run-all` for full validation.
4. **Forgetting the portable import relocation**: new code embedded in generated workflows must use
   `csorchestrator.portable` imports so `relocate_portable_imports()` can rewrite them to
   `csorchestratorsdk.portable`.
5. **Stale git fixtures**: changing clone/checkout behavior without re-running `tools/regenerate_test_repo.py`
   and updating `initial_commit_sha` in `tests/csorchestrator/repo_test_data_config.py`.
6. **Leaving unresolved pre-commit/unstaged changes**: the `no-unstaged-changes` hook fails the commit if
   hooks left unstaged edits behind; re-run `pre-commit run --all-files` until green.
