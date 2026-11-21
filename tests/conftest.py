"""Opt-in markers of csorchestrator's tests (the mechanism: the root conftest.py, owned by the project template).

- ``slow``: long tests; ``git``: tests that need a remote git repository (and its token in CI). Both skipped by
  default, run with ``--run=slow`` / ``--run=git`` or ``--run-all`` (as CI does).
- ``requires("<tool>")``: tests that need an executable; skipped when it is missing, unless ``--run-all`` (see
  ``tests/csorchestrator/_archive/compilers/conftest.py``).
"""

import pytest


def pytest_optin_markers() -> dict[str, str]:
    return {"slow": "slow tests", "git": "needs access to a remote git repository"}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", 'requires(tool): needs the executable (e.g. requires("clang++"))')
