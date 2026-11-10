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
