"""Runs of GUI deployments (an application with a window, e.g. Qt + OpenGL) on the CI runners and on a developer
machine.

The CI runners have no display and no GPU: Linux runs the application in a virtual X server (``xvfb-run``) with the
software OpenGL of Mesa; Windows gets the software OpenGL of Mesa (llvmpipe) as the ``opengl32sw.dll`` Qt loads with
``QT_OPENGL=software``; macOS uses the desktop of the session and the OpenGL of the system. Nothing of this is
installed on a developer machine (the display and the GPU of the session are used).

- ``add_gui_deployment_run``: the command and the check are the project's (exit code, an assessor of the output).
- ``add_gui_deployment_smoke_test_return_0``: the common case, an executable of the deployment with ``--smoke`` that
  checks itself and exits with 0.

The deployment is run from its archive: ``create_and_upload_deployments`` (``checkout_build``) before.
"""

from pathlib import Path

from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.local_execution.step_utils import StepExecuteOnlyOn, StepSkipExecutionOnLocal
from csorchestrator.frontend.step.step_custom_command import StepInstallAptPackages, StepWinPSCommand
from csorchestrator.frontend.step.step_deployments import StepRunDeployment

GUI_DEPLOYMENT_RUN_PHASE_NAME = "Run Deployments"

# the software OpenGL of Mesa for the Windows runners (mesa-dist-win, MSVC build)
MESA_DIST_WIN_VERSION = "25.2.6"

# QT_OPENGL: the software OpenGL on Windows (opengl32sw.dll); QT_FORCE_STDERR_LOGGING: the messages of Qt in the log
# (a GUI application on Windows has no console); GALLIUM_DRIVER: the software renderer of Mesa
GUI_DEPLOYMENT_RUN_ENVIRONMENT = {"QT_OPENGL": "software", "QT_FORCE_STDERR_LOGGING": "1", "GALLIUM_DRIVER": "llvmpipe"}

# Linux: in a virtual X server when xvfb-run is there (CI), else on the display of the session (a developer machine)
_LINUX_X_SERVER_WRAPPER = [
    "sh",
    "-c",
    'if command -v xvfb-run >/dev/null; then exec xvfb-run -a "$@"; else exec "$@"; fi',
    "sh",
]


def _gui_deployment_run_phase(o: Orchestrator) -> Phase:
    """The phase of the GUI runs: created once, with the display and the software OpenGL of the CI runners first."""
    for phase in o.phases:
        if phase.name == GUI_DEPLOYMENT_RUN_PHASE_NAME:
            return phase
    p = o.create_phase(GUI_DEPLOYMENT_RUN_PHASE_NAME)
    p.add_step(
        StepInstallAptPackages(
            name="install xvfb",
            description="virtual X server for the GUI runs of the deployments",
            packages=["xvfb", "xauth"],
        )
        .add_extra(StepExecuteOnlyOn(os=OS.LINUX))
        .add_extra(StepSkipExecutionOnLocal())
    )
    p.add_step(
        StepWinPSCommand(
            name="install the software OpenGL of Mesa",
            description="Mesa llvmpipe (mesa-dist-win) as opengl32sw.dll in System32, for the GUI runs",
            cmd=[
                '$ErrorActionPreference = "Stop"',
                f'$version = "{MESA_DIST_WIN_VERSION}"',
                '$url = "https://github.com/pal1000/mesa-dist-win/releases/download/$version/mesa3d-$version-release-msvc.7z"',
                "Invoke-WebRequest -Uri $url -OutFile mesa.7z",
                "7z e mesa.7z x64/opengl32.dll x64/libgallium_wgl.dll -omesa -y",
                'Copy-Item mesa/opengl32.dll "$env:SystemRoot/System32/opengl32sw.dll"',
                'Copy-Item mesa/libgallium_wgl.dll "$env:SystemRoot/System32/libgallium_wgl.dll"',
                'Get-Item "$env:SystemRoot/System32/opengl32sw.dll", "$env:SystemRoot/System32/libgallium_wgl.dll"',
            ],
        )
        .add_extra(StepExecuteOnlyOn(os=OS.WINDOWS))
        .add_extra(StepSkipExecutionOnLocal())
    )
    return p


def add_gui_deployment_run(
    o: Orchestrator,
    *,
    deployment: str,
    command: dict[OS, list[str]],
    base_build_dir: Path,
    build_config: BuildConfig,
    archives_dir: Path,
    name: str | None = None,
    expect_exit_code: int | None = 0,
    assessor: str | None = None,
    environment: dict[str, str] | None = None,
    timeout_seconds: float = 120,
) -> None:
    """Run ``command`` (per OS; ``{folder}``: the deployment extracted from its archive) as a GUI application, in
    every configuration of ``build_config`` the deployment lists. On Linux the command runs in ``xvfb-run`` when
    there; the system packages of the deployment (``system-requirements.txt``) are installed first in CI.

    The check: the exit code (``expect_exit_code``, None: any) and ``assessor``, ``"module:function"`` of a module
    of the project (its root on the import path; the standard library and ``csorchestratorsdk`` only) that gets a
    ``DeploymentRunOutput`` (exit code, output) and returns the errors. ``environment``: on top of
    ``GUI_DEPLOYMENT_RUN_ENVIRONMENT``."""
    commands = dict(command)
    if OS.LINUX in commands:
        commands[OS.LINUX] = [*_LINUX_X_SERVER_WRAPPER, *commands[OS.LINUX]]
    _gui_deployment_run_phase(o).add_step(
        StepRunDeployment(
            name=name or f"Run of the deployment {deployment}",
            description=f"start the deployment {deployment} as a GUI application and check it",
            deployment=deployment,
            command=commands,
            base_build_dir=base_build_dir,
            build_config=build_config,
            archives_dir=archives_dir,
            install_system_requirements=True,
            expect_exit_code=expect_exit_code,
            assessor=assessor,
            environment={**GUI_DEPLOYMENT_RUN_ENVIRONMENT, **(environment or {})},
            timeout_seconds=timeout_seconds,
        )
    )


def add_gui_deployment_smoke_test_return_0(
    o: Orchestrator,
    *,
    deployment: str,
    executable: str,
    base_build_dir: Path,
    build_config: BuildConfig,
    archives_dir: Path,
    arguments: list[str] | None = None,
    timeout_seconds: float = 120,
) -> None:
    """The smoke test of a GUI application: ``executable`` (relative to the deployment, without ``.exe``, e.g.
    ``bin/app``) started with ``arguments`` (default ``--smoke``) on Linux, Windows and macOS; it checks itself and
    passes with the exit code 0."""
    arguments = ["--smoke"] if arguments is None else arguments
    add_gui_deployment_run(
        o,
        deployment=deployment,
        command={
            OS.LINUX: [f"{{folder}}/{executable}", *arguments],
            OS.WINDOWS: [f"{{folder}}/{executable}.exe", *arguments],
            OS.MACOS: [f"{{folder}}/{executable}", *arguments],
        },
        base_build_dir=base_build_dir,
        build_config=build_config,
        archives_dir=archives_dir,
        name=f"Smoke test of the deployment {deployment}",
        expect_exit_code=0,
        timeout_seconds=timeout_seconds,
    )
