from dataclasses import dataclass
from pathlib import Path

from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import (
    StepBase,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    create_context_os_architecture_compiler_generator_string_github_matrix,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepGitHubUploadArtifacts,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.portable.release_manifest import ReleaseManifest


@dataclass
class StepUploadArtifactsCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepUploadArtifacts"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_upload_artifacts_to_githubwf(self.step, wf_job, reporter_sink)


def create_artifact_prefix_from_orchestrator_name_version(o: Orchestrator) -> str:
    return o.name_version_to_string() + "-"


@dataclass
class StepUploadArtifacts(StepBase):
    base_install_dir: Path
    artifact_prefix: str

    def __post_init__(self) -> None:
        self.add_capability(StepUploadArtifactsCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)


def step_upload_artifacts_to_githubwf(
    step: StepUploadArtifacts, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    install_subdir = create_context_os_architecture_compiler_generator_string_github_matrix()

    artifact_name = f"{step.artifact_prefix}{install_subdir}"

    steps: list[GithubStepInterface] = [
        StepGitHubUploadArtifacts(
            name=step.name,
            with_name=artifact_name,
            with_path=[
                (step.base_install_dir / "*.tar.gz").as_posix(),
                (step.base_install_dir / ("*" + ReleaseManifest.CSORCHESTRATOR_MANIFEST_EXTENSION)).as_posix(),
            ],
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
