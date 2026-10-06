from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import (
    StepBase,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    create_context_os_architecture_compiler_generator_string_github_matrix,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import StepRunCommand
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.local_execution.context_local_execution import (
    ContextLocalExecution,
)
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import StepCapabilityLocalExecution
from csorchestrator.frontend.step.templates.utils import (
    fix_path_repr,
    relocate_portable_imports,
    replace_template_variable,
)
from csorchestrator.portable.package_version import (
    CMakeConfigPackageVersionGrep,
    PackageVersion,
)
from csorchestrator.portable.release_manifest import (
    ReleaseManifest,
    get_package_versions_and_write_single_variant_manifest,
)


@dataclass
class StepGetVersionsFromCMakeConfigPackageVersionCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepGetVersionsFromCMakeConfigPackageVersion"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_get_versions_from_cmake_config_package_version_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepGetVersionsFromCMakeConfigPackageVersionCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepGetVersionsFromCMakeConfigPackageVersion"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_get_versions_from_cmake_config_package_version(self.step, context, reporter_sink)


@dataclass
class StepGetVersionsFromCMakeConfigPackageVersion(StepBase):
    base_install_dir: Path
    repos_config_file_list: list[CMakeConfigPackageVersionGrep] = field(default_factory=list)
    repos_auto_search_list: list[str] = field(default_factory=list)  # name of repos only,
    repos_version: list[PackageVersion] = field(default_factory=list)
    # will look for {name}-config-version.cmake or {name}ConfigVersion.cmake

    def __post_init__(self) -> None:
        self.add_capability(
            StepGetVersionsFromCMakeConfigPackageVersionCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow
        )
        self.add_capability(
            StepGetVersionsFromCMakeConfigPackageVersionCapabilityLocalExecution(self), StepCapabilityLocalExecution
        )


def create_version_file_name(
    orchestrator_name_and_version_string: str, context_os_architecture_compiler_generator_string: str
) -> str:
    return (
        orchestrator_name_and_version_string
        + "-"
        + context_os_architecture_compiler_generator_string
        + ReleaseManifest.CSORCHESTRATOR_MANIFEST_EXTENSION
    )


def execute_step_get_versions_from_cmake_config_package_version(
    step: StepGetVersionsFromCMakeConfigPackageVersion, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    context_os_architecture_compiler_generator_string = create_context_os_architecture_compiler_generator_string(
        context.get_active_os_architecture_compiler_generator()
    )

    output_file = (
        context.base_folder_path
        / step.base_install_dir
        / Path(
            create_version_file_name(
                context.orchestrator_description.name_and_version_string,
                context_os_architecture_compiler_generator_string,
            )
        )
    )

    errors_list = get_package_versions_and_write_single_variant_manifest(
        repos_config_file_list=step.repos_config_file_list,
        repos_auto_search_list=step.repos_auto_search_list,
        repos_version=step.repos_version,
        base_install_dir=context.base_folder_path / step.base_install_dir,
        install_subdir=Path(context_os_architecture_compiler_generator_string),
        variant_string=context_os_architecture_compiler_generator_string,
        project_name=context.orchestrator_description.orchestrator_name,
        project_version=context.orchestrator_description.orchestrator_version,
        output_file=output_file,
    )

    for e in errors_list:
        report.append_error(e)

    return report


def step_get_versions_from_cmake_config_package_version_to_githubwf(
    step: StepGetVersionsFromCMakeConfigPackageVersion,
    context: JobOrchestratorMatrixExecutionContext,
    reporter_sink: ReporterSinkBase,
) -> OptionalListGithubStepsWithReport:

    context_os_architecture_compiler_generator_string = (
        create_context_os_architecture_compiler_generator_string_github_matrix()
    )
    output_file = step.base_install_dir / Path(
        create_version_file_name(
            context.orchestrator_description.name_and_version_string,
            context_os_architecture_compiler_generator_string,
        )
    )
    template_file = (
        files("csorchestrator.frontend.step")
        .joinpath("templates")
        .joinpath("get_versions_from_cmake_config_package_version.py")
    )
    python_code = template_file.read_text(encoding="utf-8")

    python_code = relocate_portable_imports(python_code)

    python_code = replace_template_variable(
        python_code, "repos_config_file_list", fix_path_repr(repr(step.repos_config_file_list))
    )
    python_code = replace_template_variable(python_code, "repos_auto_search_list", repr(step.repos_auto_search_list))
    python_code = replace_template_variable(python_code, "repos_version", repr(step.repos_version))

    python_code = replace_template_variable(python_code, "base_install_dir", fix_path_repr(repr(step.base_install_dir)))

    python_code = replace_template_variable(
        python_code, "install_subdir", fix_path_repr(repr(Path(context_os_architecture_compiler_generator_string)))
    )

    python_code = replace_template_variable(
        python_code, "variant_string", repr(context_os_architecture_compiler_generator_string)
    )
    python_code = replace_template_variable(
        python_code,
        "project_name",
        repr(
            context.orchestrator_description.orchestrator_name,
        ),
    )
    python_code = replace_template_variable(
        python_code,
        "project_version",
        repr(
            context.orchestrator_description.orchestrator_version,
        ),
    )

    python_code = replace_template_variable(python_code, "output_file", fix_path_repr(repr(output_file)))

    python_lines = python_code.splitlines()

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name="Get Versions", shell_type="python", run=python_lines, env={"PYTHONPATH": "${{ github.workspace }}"}
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
