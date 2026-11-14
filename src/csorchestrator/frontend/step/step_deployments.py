"""Steps for the deployments of a csCMake build (``cs_deployment``): archive them (CI artifacts, release assets), run
them (e.g. a smoke run of the deployed application).

The folders of the deployments come from ``cs-deployments.json`` of the builds of the variant
(``<base_build_dir>/<variant>/...``), in the configurations of the build (``build_config``). The logic is in
``csorchestrator.portable.deployments``: the same code runs locally and in the generated GitHub workflow.
"""

from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    create_context_os_architecture_compiler_generator_string_github_matrix,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepGitHubUploadArtifacts,
    StepRunCommand,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import StepCapabilityLocalExecution
from csorchestrator.frontend.step.templates.utils import (
    fix_path_repr,
    relocate_portable_imports,
    replace_template_variable,
)
from csorchestrator.portable.deployments import (
    DeploymentArchives,
    DeploymentRun,
    create_deployment_archives,
    run_deployment,
)


def _template(name: str, values: dict[str, str]) -> list[str]:
    """The lines of the template ``templates/<name>``, its variables replaced by ``values`` (Python expressions)."""
    code = files("csorchestrator.frontend.step").joinpath("templates").joinpath(name).read_text(encoding="utf-8")
    code = relocate_portable_imports(code)
    for variable, value in values.items():
        code = replace_template_variable(code, variable, value)
    return code.splitlines()


def _local_variant(context: ContextLocalExecution) -> str:
    return create_context_os_architecture_compiler_generator_string(
        context.get_active_os_architecture_compiler_generator()
    )


# --- archives ---


@dataclass
class StepCreateDeploymentArchivesCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepCreateDeploymentArchives"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_create_deployment_archives_to_githubwf(self.step, wf_job)


@dataclass
class StepCreateDeploymentArchivesCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepCreateDeploymentArchives"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_create_deployment_archives(self.step, context)


@dataclass(kw_only=True)
class StepCreateDeploymentArchives(StepBase):
    """Archive the deployments of the builds of the variant (``.zip`` on Windows, else ``.tar.gz``) in
    ``output_dir``: ``<project>-<version>-<variant>-<deployment>-<config>``. A deployment the build should have made
    (a configuration it lists, built) and not found fails. In GitHub, the archives are uploaded as artifacts: the
    release job attaches them to the release."""

    base_build_dir: Path
    build_config: BuildConfig
    output_dir: Path

    def __post_init__(self) -> None:
        self.add_capability(StepCreateDeploymentArchivesCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepCreateDeploymentArchivesCapabilityLocalExecution(self), StepCapabilityLocalExecution)


def execute_step_create_deployment_archives(
    step: StepCreateDeploymentArchives, context: ContextLocalExecution
) -> Report:
    report = Report()
    variant = _local_variant(context)
    description = context.orchestrator_description
    for error in create_deployment_archives(
        build_dir=(context.base_folder_path / step.base_build_dir / variant).resolve(),
        build_config=step.build_config.value,
        project_name=description.orchestrator_name,
        project_name_and_version=description.name_and_version_string,
        variant=variant,
        output_dir=(context.base_folder_path / step.output_dir).resolve(),
        log=report.append_info,
    ):
        report.append_error(error)
    return report


def step_create_deployment_archives_to_githubwf(
    step: StepCreateDeploymentArchives, wf_job: JobOrchestratorMatrixExecutionContext
) -> OptionalListGithubStepsWithReport:
    variant = create_context_os_architecture_compiler_generator_string_github_matrix()
    description = wf_job.orchestrator_description
    lines = _template(
        "create_deployment_archives.py",
        {
            "build_dir": fix_path_repr(repr(step.base_build_dir / variant)),
            "build_config": repr(step.build_config.value),
            "project_name": repr(description.orchestrator_name),
            "project_name_and_version": repr(description.name_and_version_string),
            "variant": repr(variant),
            "output_dir": fix_path_repr(repr(step.output_dir)),
        },
    )
    # PYTHONPATH: the template imports csorchestratorsdk, copied at the root of the checkout of the project
    steps: list[GithubStepInterface] = [
        StepRunCommand(name=step.name, shell_type="python", run=lines, env={"PYTHONPATH": "${{ github.workspace }}"}),
        StepGitHubUploadArtifacts(
            name=f"{step.name}: upload",
            with_name=f"{description.name_and_version_string}-{variant}-deployments",
            with_path=[(step.output_dir / "*.tar.gz").as_posix(), (step.output_dir / "*.zip").as_posix()],
        ),
    ]
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())


# --- runs ---


@dataclass
class StepRunDeploymentCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepRunDeployment"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_run_deployment_to_githubwf(self.step, wf_job)


@dataclass
class StepRunDeploymentCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepRunDeployment"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_run_deployment(self.step, context)


@dataclass(kw_only=True)
class StepRunDeployment(StepBase):
    """Run a command on a deployment extracted from its archive (``archives_dir``, StepCreateDeploymentArchives before)
    in a temporary folder outside the workspace (``{folder}`` in the command), in every configuration of the build the
    deployment lists, e.g. a smoke run of the deployed application. The command per OS (an OS without: not run);
    ``clean_environment``: nothing to find libraries with (system folders only on PATH);
    ``install_system_requirements``: in CI on Linux, ``apt-get install`` the packages of ``system-requirements.txt``
    first (never locally). Another exit code than ``expect_exit_code``, or a run longer than ``timeout_seconds``,
    fails."""

    deployment: str
    command: dict[OS, list[str]]
    base_build_dir: Path
    build_config: BuildConfig
    archives_dir: Path
    clean_environment: bool = True
    install_system_requirements: bool = False
    expect_exit_code: int = 0
    timeout_seconds: float = 120
    _commands_by_os: dict[str, list[str]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._commands_by_os = {os.value: command for os, command in self.command.items()}
        self.add_capability(StepRunDeploymentCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepRunDeploymentCapabilityLocalExecution(self), StepCapabilityLocalExecution)


def execute_step_run_deployment(step: StepRunDeployment, context: ContextLocalExecution) -> Report:
    report = Report()
    command = step.command.get(context.os_architecture.os)
    if command is None:
        report.append_info(f"deployment {step.deployment}: no command on {context.os_architecture.os.value}, not run")
        return report
    run = DeploymentRun(
        deployment=step.deployment,
        command=command,
        clean_environment=step.clean_environment,
        install_system_requirements=False,  # never sudo apt-get on a developer machine
        expect_exit_code=step.expect_exit_code,
        timeout_seconds=step.timeout_seconds,
    )
    variant = _local_variant(context)
    description = context.orchestrator_description
    archives = DeploymentArchives(
        (context.base_folder_path / step.archives_dir).resolve(),
        description.orchestrator_name,
        description.name_and_version_string,
        variant,
    )
    build_dir = (context.base_folder_path / step.base_build_dir / variant).resolve()
    for error in run_deployment(build_dir, step.build_config.value, run, archives, log=report.append_info):
        report.append_error(error)
    return report


def step_run_deployment_to_githubwf(
    step: StepRunDeployment, wf_job: JobOrchestratorMatrixExecutionContext
) -> OptionalListGithubStepsWithReport:
    variant = create_context_os_architecture_compiler_generator_string_github_matrix()
    description = wf_job.orchestrator_description
    lines = _template(
        "run_deployment.py",
        {
            "build_dir": fix_path_repr(repr(step.base_build_dir / variant)),
            "build_config": repr(step.build_config.value),
            "deployment": repr(step.deployment),
            "archives_dir": fix_path_repr(repr(step.archives_dir)),
            "project_name": repr(description.orchestrator_name),
            "project_name_and_version": repr(description.name_and_version_string),
            "variant": repr(variant),
            "commands": repr(step._commands_by_os),
            "clean_environment": repr(step.clean_environment),
            "install_system_requirements": repr(step.install_system_requirements),
            "expect_exit_code": repr(step.expect_exit_code),
            "timeout_seconds": repr(float(step.timeout_seconds)),
        },
    )
    # PYTHONPATH: the template imports csorchestratorsdk, copied at the root of the checkout of the project
    steps: list[GithubStepInterface] = [
        StepRunCommand(name=step.name, shell_type="python", run=lines, env={"PYTHONPATH": "${{ github.workspace }}"})
    ]
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
