---
name: csorchestrator-usage
description: Using csorchestrator in a cscosine project (a <name>_project.py script with create_orchestrator(), a <name>_config.py, a dependencies/ folder with *.csOrchestratorManifest files, a csorchestratorsdk/ folder, a generated .github/workflows/<name>.yml). Use when changing what a project builds or downloads (repositories, refs, build configurations, providers and their release tags, the platform matrix, the weekly schedule, deployments and their smoke tests), regenerating the workflow, choosing the csorchestrator version of a project, or reading a failure of the generated CI. Not for developing csorchestrator itself.
---

# Using csorchestrator

csorchestrator turns one Python script per project, `<name>_project.py`, into a build: run locally, or translated
into a GitHub Actions workflow (one job per platform variant) that builds `main` and the tags, and on a tag publishes a
GitHub Release with binary packages and a **manifest** (`<name>-<version>.csOrchestratorManifest`). Other projects
download those packages instead of rebuilding them: the releasing project is their **provider**.

Its API is the one of `v0.1.x`, before a planned rewrite: copy the patterns of the existing project scripts below
rather than inventing new calls, and read the source (`src/csorchestrator/application/recipes/`) for the arguments.

## The files of a project

| File | What it is | Edited by |
|---|---|---|
| `<name>_project.py` | the recipe: `create_orchestrator()` builds the `Orchestrator`; `main()` makes the script the CLI | hand |
| `<name>_config.py` | what the project needs from its providers (`external_dependencies`), its library list; a provider also ships it in its release (`additional_files_list`) for its consumers | hand |
| `dependencies/` | the providers' manifests and their `<provider>_config.py`, downloaded each time the script builds its orchestrator (any command; the provider releases must exist) | generated: never by hand |
| `csorchestratorsdk/portable/` | code the generated jobs run, copied from csorchestrator | generated: never by hand |
| `.github/workflows/<name>.yml` | the CI | generated: never by hand |
| `setup.sh` / `setup.ps1` | venv + the pinned csorchestrator (template-owned) | template |

## Commands

```bash
./setup.sh                                   # the pinned csorchestrator version (a template answer)
./setup.sh --csorchestrator=v0.1.1-rc1       # another tag or branch of github.com/cscosine/csorchestrator
./setup.sh --csorchestrator=../csorchestrator  # a local clone, editable (while changing csorchestrator)
source .venv/bin/activate

./<name>_project.py describe                  # phases, steps, matrix: no build
./<name>_project.py generate-github-workflow  # writes .github/workflows/<name>.yml, refreshes csorchestratorsdk/
./<name>_project.py                           # = run: the whole build locally (long; see below)
```

Global options: `--sink {print,colored,colorama,none}`, `--markdown <file>` (a Markdown report). The console script
`csorchestrator run|describe|generate-github-workflow <script>` does the same.

After **any** change of the project script or `<name>_config.py`: `generate-github-workflow`, then commit the script,
the workflow, `dependencies/` and `csorchestratorsdk/` together. A hand edit of the workflow is overwritten next time.

Do not run the full build locally to check a change: it checks out and builds every repository, downloads every
provider, for hours. `describe` and `generate-github-workflow` are the checks; CI builds (a tag build is the test of a
release; a `feature/*` branch: `gh workflow run <name>.yml --ref feature/<topic>`).

## The project script

The shape every project uses (see `csImgTracker_project.py`, `csfoundation_project.py`):

```python
o = create_default_orchestrator(
    name="myProject", version="0.2.0",              # the release version: also in pyproject.toml, project(VERSION)
    base_install_dir=Path("_csw/install"),
    schedule=Cron.weekly(DayOfWeek.MON, hour=4, minute=40),   # UTC; its own slot of the weekly queue
    additional_files_list=[Path("myProject_config.py")],      # a provider: shipped to its consumers
    additional_matrix_list=get_context_list_linux("ubuntu26.04") + get_context_list_macos("macos15"),
)
checkout_repos(o, base_target_dir=Path("_csw"),
               repo_ref_dict=extract_repo_ref_dict(repos),                      # inner libraries, at "main"
               release_archive_list=[create_cscmake_release_archive("1.1.0")])  # csCMake by release
install_<name>_build_dependencies(...)          # from <name>_config.py: providers' packages into _csw/libs
build_repos(o, base_target_dir=Path("_csw"), repo_build_config_dict=..., build_self=BuildConfig.DEBUG_RELEASE)
create_and_upload_artifacts(o, base_install_dir=..., repos_auto_search_list=[...])
create_and_upload_deployments(o, base_build_dir=..., build_config=..., output_dir=...)   # csCMake cs_deployment
add_gui_deployment_smoke_test_return_0(o, deployment="app", executable="bin/app", ...)  # runs the deployment
```

`base_target_dir` is the workspace of csCMake's standalone layout, `_csw` (`${sourceDir}/_csw/csCMake/...` in the
project's `csCMakeProjectSetup.json`): a local run stops before building the project's own sources when they differ.

| Need | Where |
|---|---|
| an inner library (built here) and its ref | `repos = {"csCore": RepoRefBuildPublishConfig("main", BuildConfig....)}`; a `feature/<topic>` ref while a change spans repositories, back to `main` before merging |
| configurations built | `BuildConfig`: `DEBUG`, `RELEASE`, `RELWITHDEBINFO`, `PARANOID`, `DEBUG_RELEASE`, `DEBUG_RELEASE_RELWITHDEBINFO_PARANOID`; `None` = checkout only. Must be configurations of the CMake project (csCMake `cs_initialize_project`) |
| platforms | default matrix: Ubuntu 22.04 / 24.04 (x64, arm64; GCC, Clang), Windows (MSVC, clang-cl; Visual Studio, Ninja); opt-in: `get_context_list_linux("ubuntu26.04")`, `get_context_list_macos("macos15" / "macos26")` in `additional_matrix_list` |
| csCMake version | `create_cscmake_release_archive("<version>")`: always a release |
| prebuilt libraries of another project | `<name>_config.py`: a `ManifestGithub(org="cscosine", git_repo=..., project_name=..., project_version=..., release_tag="v...")` per provider, and `external_dependencies = {provider: {"<my lib>": ["<their lib>", ...]}}`; the provider's own mapping function by name (e.g. csqt6: `"qt6_mapping"`) |
| weekly run | `schedule=Cron.weekly(...)` (UTC): a slot after the projects it depends on, never the default (Monday 03:00 UTC); the queue is in `cscosine/.github` `ECOSYSTEM.md` |
| triggers | default: push to `main`, tags `v*.*.*`; no PR builds |

## Releases

1. Versions aligned in the release commit: `create_default_orchestrator(version=...)`, `pyproject.toml`, CMake
   `project(VERSION)`; providers in `<name>_config.py` at released tags; csCMake at a release.
2. Tag `vX.Y.Z-rcN` on `main`: the build publishes a pre-release with the packages and the manifest; consumers can
   point to it. Green: tag `vX.Y.Z` on the same commit (it publishes the release), then
   `git push origin vX.Y.Z:stable`. Red: fix, next rc number (tags are never moved).
3. Libraries built by a distribution get their own tags on the commits used (the manifest records ref, commit, tag).

The order between projects (release chain): csorchestrator, csCMake → third_party_base_libs → csqt6, csopencvcpu,
csopencvcuda → csfoundation → csoptimization → applications. The `cs-org` plugin's `cs-release-train` skill drives a
release across them.

## Reading a CI failure

- The job name is the variant (`csv1-<os>-...-<generator>`), the steps are the phases of the script (`describe`
  lists them). Reproduce one variant with the csCMake presets (`cmake --workflow --preset ...`) rather than `run`.
- "manifest" / download errors: the provider tag in `<name>_config.py` has no release (yet), or the library name is
  not in its manifest (`dependencies/<provider>-<version>.csOrchestratorManifest` lists them).
- A workflow out of date with the script: regenerate, never patch the YAML.
- A project moves to a new csorchestrator in planned rounds: the `setup.sh` pin (a template answer,
  `csorchestrator_version`), `./setup.sh`, then `generate-github-workflow`.
