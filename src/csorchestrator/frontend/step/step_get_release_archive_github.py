from dataclasses import dataclass
from pathlib import Path

from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import StepCapabilityLocalExecution
from csorchestrator.frontend.step.github_release_download import (
    DownloadGithubFileEntry,
    download_and_extract_github_release_asset,
    github_release_download_and_extract_steps,
)


@dataclass
class StepGetReleaseArchiveGithubCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepGetReleaseArchiveGithub"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_get_release_archive_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepGetReleaseArchiveGithubCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepGetReleaseArchiveGithub"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_get_release_archive(self.step, context, reporter_sink)


@dataclass
class StepGetReleaseArchiveGithub(StepBase):
    """
    Download a .tar.gz release asset, the same for every variant (e.g. a tool such as csCMake), and extract it into
    extract_dir; the archive is deleted after the extraction.
    """

    archive: DownloadGithubFileEntry
    extract_dir: str

    def __post_init__(self) -> None:
        self.add_capability(StepGetReleaseArchiveGithubCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepGetReleaseArchiveGithubCapabilityLocalExecution(self), StepCapabilityLocalExecution)


def execute_step_get_release_archive(
    step: StepGetReleaseArchiveGithub, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    extract_dir = (context.base_folder_path / step.extract_dir).resolve()
    extract_dir.mkdir(parents=True, exist_ok=True)
    return download_and_extract_github_release_asset(step.archive, extract_dir)


def step_get_release_archive_to_githubwf(
    step: StepGetReleaseArchiveGithub, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:
    steps = github_release_download_and_extract_steps(
        name=step.name, entry=step.archive, target_dir=Path(step.extract_dir).as_posix()
    )
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
