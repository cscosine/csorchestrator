"""The GUI runs of deployments: one phase with the display / software OpenGL of the CI runners, then the runs."""

import re
from pathlib import Path

from csorchestrator.application.recipes.create_orchestrator import create_default_orchestrator
from csorchestrator.application.recipes.gui_deployments import (
    GUI_DEPLOYMENT_RUN_ENVIRONMENT,
    GUI_DEPLOYMENT_RUN_PHASE_NAME,
    MESA_DIST_WIN_SHA256,
    MESA_DIST_WIN_VERSION,
    add_gui_deployment_run,
    add_gui_deployment_smoke_test_return_0,
)
from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.step.step_custom_command import StepWinPSCommand
from csorchestrator.frontend.step.step_deployments import StepRunDeployment

COMMON = {
    "base_build_dir": Path("_csw/build"),
    "build_config": BuildConfig.RELEASE,
    "archives_dir": Path("_csw/deploy-archives"),
}


def test_smoke_test_return_0_and_a_run_with_an_assessor_share_one_phase() -> None:
    o = create_default_orchestrator(name="app", version="1.0.0", base_install_dir=Path("_csw/install"))
    add_gui_deployment_smoke_test_return_0(o, deployment="sample", executable="bin/sample", **COMMON)  # type: ignore[arg-type]
    add_gui_deployment_run(
        o,
        deployment="app",
        command={OS.MACOS: ["{folder}/bin/app", "--check"]},
        expect_exit_code=None,
        assessor="app_assessors:check",
        environment={"QT_OPENGL": "desktop", "EXTRA": "1"},
        **COMMON,  # type: ignore[arg-type]
    )

    phases = [p for p in o.phases if p.name == GUI_DEPLOYMENT_RUN_PHASE_NAME]
    assert len(phases) == 1
    names = [s.name for s in phases[0].steps]
    assert names == [
        "install xvfb",
        "install the software OpenGL of Mesa",
        "Smoke test of the deployment sample",
        "Run of the deployment app",
    ]
    smoke, app = (s for s in phases[0].steps if isinstance(s, StepRunDeployment))

    assert smoke.command[OS.LINUX][-2:] == ["{folder}/bin/sample", "--smoke"]
    assert smoke.command[OS.LINUX][0] == "sh"  # xvfb-run when there
    assert smoke.command[OS.WINDOWS] == ["{folder}/bin/sample.exe", "--smoke"]
    assert smoke.command[OS.MACOS] == ["{folder}/bin/sample", "--smoke"]
    assert smoke.expect_exit_code == 0 and smoke.assessor is None
    assert smoke.environment == GUI_DEPLOYMENT_RUN_ENVIRONMENT
    assert smoke.install_system_requirements

    assert app.command == {OS.MACOS: ["{folder}/bin/app", "--check"]}
    assert app.expect_exit_code is None and app.assessor == "app_assessors:check"
    assert app.environment == {**GUI_DEPLOYMENT_RUN_ENVIRONMENT, "QT_OPENGL": "desktop", "EXTRA": "1"}


def test_mesa_is_checked_against_its_sha256_before_use() -> None:
    """The software OpenGL of Mesa comes from a download: the step checks its SHA-256 and fails on a mismatch, before
    anything is extracted or copied."""
    assert re.fullmatch(r"[0-9a-f]{64}", MESA_DIST_WIN_SHA256)
    o = create_default_orchestrator(name="app", version="1.0.0", base_install_dir=Path("_csw/install"))
    add_gui_deployment_smoke_test_return_0(o, deployment="sample", executable="bin/sample", **COMMON)  # type: ignore[arg-type]
    (phase,) = (p for p in o.phases if p.name == GUI_DEPLOYMENT_RUN_PHASE_NAME)
    (mesa,) = (s for s in phase.steps if isinstance(s, StepWinPSCommand))

    cmd = mesa.cmd
    assert cmd[0] == '$ErrorActionPreference = "Stop"'
    download = next(i for i, c in enumerate(cmd) if c.startswith("Invoke-WebRequest") and "-OutFile mesa.7z" in c)
    assert any(f'"{MESA_DIST_WIN_VERSION}"' in c for c in cmd[:download])
    check = next(i for i, c in enumerate(cmd) if "Get-FileHash mesa.7z -Algorithm SHA256" in c)
    expected = next(i for i, c in enumerate(cmd) if c == f'$expected = "{MESA_DIST_WIN_SHA256}"')
    fail = next(i for i, c in enumerate(cmd) if c.startswith("if ($actual -ne $expected) { throw"))
    first_use = next(i for i, c in enumerate(cmd) if c.startswith("7z ") or c.startswith("Copy-Item"))
    assert download < expected < fail < first_use and download < check < fail
