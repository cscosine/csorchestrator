from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
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
from csorchestrator.frontend.step.step_get_versions_from_cmake_config_package_version import (
    create_version_file_name,
)
from csorchestrator.frontend.step.templates.utils import (
    fix_path_repr,
    relocate_portable_imports,
    replace_template_variable,
)
from csorchestrator.portable.release_manifest import (
    load_release_manifest_single_variant_and_prepare_archive,
)


@dataclass
class StepCreateArchivesCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepCreateArchives"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_create_archives_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepCreateArchivesCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepCreateArchives"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_create_archives(self.step, context, reporter_sink)


@dataclass
class StepCreateArchives(StepBase):
    base_install_dir: Path

    def __post_init__(self) -> None:
        self.add_capability(StepCreateArchivesCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepCreateArchivesCapabilityLocalExecution(self), StepCapabilityLocalExecution)


# TODO: minimze code repetition between local execution and github wf


def execute_step_create_archives(
    step: StepCreateArchives, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    context_os_architecture_compiler_generator_string = create_context_os_architecture_compiler_generator_string(
        context.get_active_os_architecture_compiler_generator()
    )
    input_base_dir = Path(context.base_folder_path / step.base_install_dir).resolve()
    input_full_path = Path(
        input_base_dir
        / Path(
            create_version_file_name(
                context.orchestrator_description.name_and_version_string,
                context_os_architecture_compiler_generator_string,
            )
        )
    ).resolve()

    errors_list = load_release_manifest_single_variant_and_prepare_archive(
        input_full_path,
        context.orchestrator_description.name_and_version_string,
        context_os_architecture_compiler_generator_string,
        input_base_dir,
    )

    for e in errors_list:
        report.append_error(e)

    return report


def step_create_archives_to_githubwf(
    step: StepCreateArchives, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    context_os_architecture_compiler_generator_string = (
        create_context_os_architecture_compiler_generator_string_github_matrix()
    )
    input_base_dir = step.base_install_dir
    input_full_path = Path(
        input_base_dir
        / Path(
            create_version_file_name(
                wf_job.orchestrator_description.name_and_version_string,
                context_os_architecture_compiler_generator_string,
            )
        )
    )

    template_file = files("csorchestrator.frontend.step").joinpath("templates").joinpath("create_archives.py")
    python_code = template_file.read_text(encoding="utf-8")

    python_code = relocate_portable_imports(python_code)

    python_code = replace_template_variable(python_code, "input_full_path", fix_path_repr(repr(input_full_path)))
    python_code = replace_template_variable(
        python_code, "project_name_and_version", repr(wf_job.orchestrator_description.name_and_version_string)
    )
    python_code = replace_template_variable(
        python_code,
        "context_os_architecture_compiler_generator_string",
        repr(context_os_architecture_compiler_generator_string),
    )
    python_code = replace_template_variable(python_code, "input_base_dir", fix_path_repr(repr(input_base_dir)))

    python_lines = python_code.splitlines()

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name="Create Archives", shell_type="python", run=python_lines, env={"PYTHONPATH": "${{ github.workspace }}"}
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
