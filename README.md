# csorchestrator

## 📦 Project Overview

csorchestrator is a centralized project manager

## 📁 Repository Structure

```
csorchestrator/
├── src/csorchestrator/              # installable package (src-layout)
│   ├── application/                 # CLI, recipes and orchestrator factory
│   ├── domain/                      # domain model: Orchestrator, phases, steps, contexts
│   ├── foundation/                  # generic building blocks (Report, Expected, git/fs helpers)
│   ├── frontend/                    # visitors & steps: validation, local execution, GitHub Actions
│   ├── portable/                    # self-contained SDK (package_version, release_manifest)
│   ├── _archive/                    # archived code kept for reference
│   └── py.typed                     # PEP 561 type-annotation marker
├── tests/                           # pytest suites mirroring src/ (excluded from linting)
├── tools/                           # maintenance helpers (e.g. .vscode/launch.json generator)
├── .github/workflows/ci.yml         # GitHub Actions CI pipeline
├── conftest.py                      # pytest custom markers (slow, git, requires) and CLI flags
├── pyproject.toml                   # project metadata, deps, and tool config (ruff, mypy, pytest, import-linter)
├── constraints-minimum.txt          # pinned minimum dependency versions for CI
├── .pre-commit-config.yaml          # pre-commit hooks (ruff, mypy, unstaged-changes check)
├── .vscode/                         # debug configurations and tasks (launch.json is auto-generated)
├── .gitignore                       # git ignore patterns
├── .gitattributes                   # line-ending normalization
├── LICENSE                          # MIT license
├── setup.sh / setup.ps1             # one-time dev environment setup scripts
├── open-code.sh / open-code.ps1     # open VS Code with the virtual env activated
└── README.md                        # this file
```

---

## 🛠 Development Setup

### ⚡ Quick Start

#### Fastest Way (Using Setup Scripts)

**LINUX/MACOS:**
```bash
./setup.sh              # Run ONCE to set up venv, deps, and pre-commit hooks
./open-code.sh         # Open VS Code with venv activated
```

or
```
source ./open-code.sh         # Open VS Code with venv activated
```
to also keep the terminal with `venv` activated available

**Windows (PowerShell):**
```powershell
.\\setup.ps1           # Run ONCE to set up venv, deps, and pre-commit hooks
.\\open-code.ps1      # Open VS Code with venv activated
```

- **`setup.sh` / `setup.ps1`** _(one-time only)_ – Automates: create venv, install deps, install pre-commit hooks
- **`open-code.sh` / `open-code.ps1`** _(convenient shortcut)_ – Activates the virtual environment and opens VS Code (useful for subsequent sessions)

#### Manual Step-by-Step

```bash
# 1. Clone repository
git clone git@github.com:cscosine/csorchestrator.git
cd csorchestrator

# 2. Create virtual environment
python3.XX -m venv .venv # 3.XX >= 3.11
source .venv/bin/activate

# 3. Install package in editable mode with dev dependencies
pip install -e .[dev]

# this
# - Installs the project `.` in editable mode (because of `-e`)
# - Installs the optional dependency group dev normally.

# 4. Run tests directly (package is now importable)
pytest

# 5. Or use pre-commit hooks
pre-commit install
pre-commit run --all-files
```

---


### 🌍 Detailed Setup

If you prefer step-by-step instructions:

#### Clone Repository

``` bash
git clone git@github.com:cscosine/csorchestrator.git
```

or

``` bash
git clone https://github.com/cscosine/csorchestrator.git
```

---

### Create Virtual Environment

``` bash
python -m venv .venv
source .venv/bin/activate
```
_Note_: You may need `python3` instead of `python`.

On Windows:

``` bash
.venv\Scripts\activate
```

or for PowerShell

``` bash
.venv\Scripts\activate.ps1
```

---

### Install Development Dependencies

All development tools are listed as optional dependencies in `pyproject.toml`:

```bash
pip install -e .[dev]
```

This installs:
- `pytest` - Testing framework
- `mypy` - Static type checking
- `ruff` - Linting and formatting
- `pre-commit` - Git hook automation


---

### Install Pre-Commit Hooks

``` bash
pre-commit install
```

Pre-commit hooks run automatically before each commit.

---

### Bump precommit hooks to last version

``` bash
pre-commit autoupdate
```

will update the `rev` version in `.pre-commit-config.yaml`

or

``` bash
pre-commit autoupdate --repo https://github.com/pre-commit/mirrors-mypy
```

to bump version of a specific repo only


---

### 🔍 Run Pre-Commit Manually

``` bash
pre-commit run --all-files
```

---

## 🔧 VS Code Helpers

This project includes VS Code configurations for streamlined development:

### Launch Configurations (Debugging)

The `.vscode/launch.json` file contains pre-configured debug configurations:

- **▶ Debug all tests** – Runs all pytest tests with debugger enabled (`-s` flag for output)
- **📁 Module-level test suites** – Quick debug access to test directories:
  - `tests/csorchestrator/context`
  - `tests/csorchestrator/core`
  - `tests/csorchestrator/orchestrator`
  - `tests/csorchestrator/step`
  - `tests/csorchestrator/utils/filesystem`
  - `tests/csorchestrator/utils/git`
- **🧪 Individual test cases** – Auto-generated configurations for specific test functions

**How to use:**
1. Open the Debug view (Ctrl+Shift+D / Cmd+Shift+D)
2. Select a configuration from the dropdown
3. Press F5 or click "Run and Debug"

_Note: `launch.json` is **fully auto-generated** by a tool in `tools/`. It's automatically kept in sync and validated by a pre-commit hook, so you should never edit it manually._

### Build & Development Tasks

The `.vscode/tasks.json` file provides convenient task runners:

- **Create venv** – Creates a Python virtual environment at `.venv`
- **Install deps** – Installs the package in editable mode with dev dependencies
- **Pre-commit install** – Sets up git hooks for automatic checks
- **Pre-commit run (all files)** – Manually trigger all pre-commit checks
- **Setup Project** – Runs all tasks above in sequence (recommended for initial setup)

**How to use:**
1. Open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
2. Type "Tasks: Run Task"
3. Select the task you want to run

Alternatively, use the terminal: `./setup.sh` or `./setup.ps1`.

---

## ✅ Toolchain

-   Formatting & Linting → Ruff
-   Pre-commit enforcement → pre-commit
-   CI → GitHub Actions

---

## Precommits

Before every commit, the project runs automated checks to guarantee consistency, formatting, and repository integrity.

The following checks are enforced:

- 🎨 **Code Formatting** – Formats Python code using `ruff-format`.
- ⚡ **Linting & Auto-Fix** – Runs `ruff` for style checks, bug detection, and automatic fixes.
- 🧠 **Type Checking** – Validates static types with `mypy`.
- 🔒 **Repository Integrity** – Fails if unstaged changes remain after hooks run (`git diff --quiet`).

If any check fails, the commit is blocked until the issues are resolved.

---

## 🧩 Reusable Module & Testing

The csorchestrator logic is a installable package in `src/csorchestrator/`. This design allows the library to be used independently-either within this repo or published on PyPI.

### Package structure (src-layout)

```
src/csorchestrator/
├── application/                 # user-facing layer: CLI, recipes, factory
│   ├── cli/                     # click-based CLI (`csorchestrator` console script)
│   ├── factory/                 # orchestrator factory helpers
│   └── recipes/                 # high-level recipes: create_default_orchestrator(),
│                                #   checkout_build_and_archive_repos(), download_manifest(), ...
├── domain/                      # pure domain model
│   ├── context/                 # OS / architecture / compiler contexts and execution matrix
│   ├── execution/               # execution state
│   └── orchestrator/            # engine: Orchestrator, Phase, StepBase, visitor & reporter bases, WorkflowConfig
├── foundation/                  # generic building blocks with no domain dependency
│   ├── core/                    # Report, Expected[T,E], OptionalResultWithReport[T]
│   ├── file_system/             # path validation, directory creation
│   └── git/                     # resolve_url, clone/checkout, validate & sync helpers
├── frontend/                    # how an Orchestrator is validated, executed and translated
│   ├── cscmake_presets/         # supported OS/arch/compiler variants for CMake projects
│   ├── github_workflow_translation/  # GitHub Actions workflow YAML generation
│   ├── local_execution/         # local execution context & executor visitor
│   ├── reporters/               # reporter sinks (print, colored, colorama, markdown, composite, dummy)
│   ├── step/                    # step definitions (clone, cmake, custom command, archives, artifacts, ...)
│   └── validation/              # validation visitor and validated orchestrator
├── portable/                    # self-contained SDK copied into client projects
│                                #   (package_version, release_manifest)
├── _archive/                    # archived code kept for reference
├── __init__.py
└── py.typed                     # PEP 561 marker for downstream type checkers
```

**Why src-layout?** It prevents import shadowing (ensures `import csorchestrator` always loads the installed package, not a local directory) and makes the structure explicit.

---

### Using the package

After installation (`pip install -e .`), you can:

1. **Use as a library:** write a *project script* that builds an `Orchestrator`. The script must
   expose a `create_orchestrator() -> OptionalResultWithReport[Orchestrator]` function; recipes from
   `application.recipes` and steps from `frontend.step` compose the phases:

    ```python
    #!/usr/bin/env python3
    import sys
    from collections.abc import Sequence
    from pathlib import Path

    from csorchestrator.application.cli.cli import orchestrator_main_with_default_run
    from csorchestrator.application.factory.factory import OptionalOrchestratorWithReport
    from csorchestrator.application.recipes.checkout_build import checkout_build_and_archive_repos
    from csorchestrator.application.recipes.create_orchestrator import create_default_orchestrator
    from csorchestrator.foundation.core.report import Report
    from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig


    def create_orchestrator() -> OptionalOrchestratorWithReport:
        report = Report()

        base_target_dir = Path("workspace")
        base_install_dir = base_target_dir / Path("install")

        # repo name -> (git ref, build config)
        repos: dict[str, tuple[str, BuildConfig | None]] = {
            "fmt": ("dev", BuildConfig.DEBUG_RELEASE),
            "Catch2": ("dev", BuildConfig.DEBUG_RELEASE),
        }

        o = create_default_orchestrator(
            name="my-project",
            version="0.1.0",
            base_install_dir=base_install_dir,
        )

        checkout_build_and_archive_repos(
            o,
            base_target_dir=base_target_dir,
            base_install_dir=base_install_dir,
            repo_ref_build_type_list=repos,
        )

        return OptionalOrchestratorWithReport.createResultAndReport(o, report)


    def main(argv: Sequence[str] | None = None) -> int:
        script_path = str(Path(__file__).resolve())
        return orchestrator_main_with_default_run(script_path, argv)


    if __name__ == "__main__":
        sys.exit(main())
    ```

    See the `3rdPartyBaseLibs` / `csQt6` repositories for full production examples.

2. **Use the CLI:** the project script is an executable entry point:

    ```bash
    # validate + execute the orchestrator locally (default command)
    python my_project.py
    # or explicitly, with a base folder for the build:
    csorchestrator run my_project.py --target-folder /tmp/build

    # generate a GitHub Actions workflow YAML from the orchestrator
    python my_project.py generate-github-workflow -o .github/workflows/ci.yml
    # or via the console script:
    csorchestrator generate-github-workflow my_project.py -o .github/workflows/ci.yml

    # reporting options (apply to run/generate-github-workflow):
    #   --sink {print,colored,colorama,none}   select the console reporter
    #   --markdown PATH                        also write an execution report as markdown
    ```

---

### Running the tests

The `tests/` directory contains pytest suites for each module (excluded from linting/type-checking).

```bash
# After installation (`pip install -e .`):
pytest
```

If you want to check code coverage, use one of

```bash
    # report to htmlcov/ folder
    pytest --cov=csorchestrator --cov-branch --cov-report=html

    # report to terminal
    pytest --cov=csorchestrator --cov-branch --cov-report=term

    # report to terminal with details on uncovered lines/blocks
    pytest --cov=csorchestrator --cov-branch --cov-report=term-missing
```

you can also combine multiple `--cov-report=` in the same command line

---

### Continuous Integration

Continuous integration runs

- repo checkout
- `pre-commit`
- pytest with coverage

on a matrix of different OS and python versions

check the `.github\workflows\ci.yml` file for details

---

### Dependencies

- **Runtime:** `click` (CLI), `PyYAML`, `GitPython`, `colorama`
- **Development:** `pytest`, `mypy`, `ruff`, `pre-commit`, `import-linter`

Install all with: `pip install -e .[dev]`
