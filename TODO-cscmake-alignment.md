# TODO: align csorchestrator with the csCMake variants

csorchestrator keeps its own copy of the variant matrix (`src/csorchestrator/frontend/cscmake_presets/supported_variants.py`
and `domain/context/*`). csCMake is the source of truth: since csCMake v0.3.0+ (`dev`, commit `7ccdf94`), its preset
generator also writes `presets/csv1/variants.json`, the supported variants as data (no code dependency between the two):

```json
{
  "schema": "csv1",
  "variants": [
    {
      "id": "csv1-linux-ubuntu22.04-x64-generic-gcc-default-ninja",
      "host": "linux", "osVersion": "ubuntu22.04", "architecture": "x64", "architectureVariant": "generic",
      "compiler": "gcc", "compiler_version": "default", "generator": "ninja", "generator_type": "singleconfig",
      "short": {"csVersion": "v1", "host": "l", "osVersion": "u22.04", "architecture": "x64", "architectureVariant": "g",
                "compiler": "g", "compiler_version": "d", "generator": "n"},
      "build_configs": ["debug", "release", "relWithDebInfo", "paranoid"]
    }
  ]
}
```

Today (2026-11-10) csCMake has 42 variants; csorchestrator lacks Ubuntu 26.04 and every macOS variant
(`get_supported_os_version_list(OS.MACOS)` returns `[]`, "TODO add MACOS support").

## Steps (one at a time, CI green before the next)

1. **Drift test.** A test reads `variants.json` from a csCMake checkout already present (sibling `../csCMake`, or a path
   in an environment variable / pytest option) and compares it with `get_supported_context_os_architecture_list()`:
   ids, every field, short forms, build configurations. Skipped (not failed) when no checkout is found; it never
   clones. In CI, the checkout is an explicit workflow step (`actions/checkout` of `cscosine/csCMake` at a pinned tag).
   Expected to fail at first, listing exactly what is missing.
2. **Ubuntu 26.04.** Version, runner label (`ubuntu-26.04`, arm64 `ubuntu-26.04-arm`), generated workflows: the same
   steps as 22.04 / 24.04. Low risk.
3. **macOS.** Versions (csCMake: `macos15`, `macos26`, arm64 only), Apple Clang (`appleclang`, short `ac`), generators
   Ninja, Ninja Multi-Config, Xcode; runner labels (`macos-15`, `macos-26`); setup steps in the generated workflows
   (Ninja: `brew install ninja` if missing; Xcode selected by the image); packaging (tar on macOS). Bigger: real CI
   iterations. csCMake's smoke workflow (`tests/smoke/ci_matrix.py`, `.github/workflows/smoke.yml`) already runs every
   macOS variant and is a working reference for the runner labels and setup steps.
4. **A selection per project** (not every variant): e.g. third_party_base_libs adds Ubuntu 26.04 GCC + Clang Ninja
   Multi-Config and macOS Apple Clang Ninja Multi-Config; then csfoundation (csCore, csLie, csCamera first;
   csVisOpenGL needs a macOS Qt from csqt6).

Later: follow `variants.json` instead of keeping the copy (generate the matrix from it, or keep the copy and let the
drift test catch every change).

## Future: read what the build declares, instead of repeating it

csCMake (`dev`, deployments) writes `cs-deployments.json` in the top build folder at configure time: each deployment
with its build target (`cs_deploy_<name>`), configurations, targets and output folder per configuration. The normal
install makes the deployments (in their configurations), so the workflow presets already make them; csorchestrator
will read the file (at run time in the GitHub job, a Python template step like `create_archives`: the file exists only
after the configure) to:

- check that each deployment was made in the configurations of the build it lists (its folder exists), and fail
  otherwise (e.g. a Debug-only run of a Release deployment);
- archive and upload each deployment folder (`<project>-<version>-<variant>-<name>-<config>`).

Deployments without csCMake (or without the file): a `Deployment` dataclass (name, configs, build target or install
component, folder per configuration) that the project script fills in by hand; `cs-deployments.json` loads into the
same class, and the steps after it are shared.

The same idea for build and install, later: a csCMake-generated description of the build (configurations, targets,
components, install prefix, the installed package and version) that csorchestrator reads, instead of deriving it
(e.g. `StepGetVersionsFromCMakeConfigPackageVersion` grepping the installed `ConfigVersion.cmake`, the install folders
assumed by `StepCreateArchives`). Alternative to evaluate: CMake's own File API (`.cmake/api/v1`, codemodel and
installers), no csCMake code but more parsing.

## Future: run the deployments in CI (a step the project configures)

The deployments made by the install (`workspace/deploy/<variant>/<project>/<name>-<config>`, csCMake `cs_deployment`)
can be run in CI, to prove they work on a machine without the build. A step the project adds in its script, e.g.:

```python
StepRunDeployment(
    deployment="app",                       # the folder from the matrix values (variant, config): cs-deployments.json
    command={                               # per OS; {folder} = the folder of the deployment
        "linux": ["xvfb-run", "-a", "{folder}/bin/csImgTracker", "--smoke"],
        "windows": ["{folder}/bin/csImgTracker.exe", "--smoke"],
        "macos": ["{folder}/bin/csImgTracker", "--smoke"],
    },
    environment="clean",                    # env -i (Linux, macOS), PATH = System32 only (Windows)
    expect_exit_code=0,                     # anything else (1, a crash) fails the job
    timeout_seconds=120,
)
```

- Done (`dev`): `StepCreateDeploymentArchives` (recipe `create_and_upload_deployments`: archives `.tar.gz`, `.zip` on
  Windows, uploaded as artifacts, attached to the release) and `StepRunDeployment` (the deployment extracted from its
  archive in a temporary folder, outside the workspace, run with a clean environment; `install_system_requirements`
  in CI on Linux). Next: csImgTracker uses them, its CI on Linux then Windows.
- The configurations: the ones the deployment lists (`cs-deployments.json`) that the build of the job built.
- Linux, a later mode: a bare container (`ubuntu:<release>`), `apt install` of the line of `system-requirements.txt`,
  then the command: proves the deployment and its list of system requirements.
- Windows: a desktop session on the runners; OpenGL without GPU: Qt's `opengl32sw.dll` shipped, `QT_OPENGL=software`.
- macOS: a desktop session on the runners (to confirm with a first run); OpenGL through the software renderer.
- csImgTracker has `--smoke` (start, check the OpenGL views got a context, exit 0; else 1); plain `offscreen` has no
  OpenGL context and csImgTracker crashes there: `xvfb-run` on Linux.
