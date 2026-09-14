from dataclasses import dataclass

from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import (
    StepBase,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import StepGitHubAction
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.step.step_custom_command import get_if_str


@dataclass
class StepAddGitHubActionCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepAddGitHubAction"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_add_github_action_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepAddGitHubAction(StepBase):
    uses: str
    id: str | None = None
    with_list: dict[str, str] | None = None

    def __post_init__(self) -> None:
        self.add_capability(StepAddGitHubActionCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)


def step_add_github_action_to_githubwf(
    step: StepAddGitHubAction, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:
    steps: list[GithubStepInterface] = [
        StepGitHubAction(
            name=step.name,
            uses=step.uses,
            id=step.id,
            if_str=get_if_str(step),
            with_list=step.with_list,
        )
    ]
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
