from dataclasses import dataclass
from typing import TypeAlias

from csorchestrator.domain.orchestrator.orchestrator_visitor_base import OrchestratorVisitorBase
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase, StepCapability
from csorchestrator.foundation.core.optional_result_with_report import OptionalResultWithReport
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_matrix_execution import (
    JobOrchestratorMatrixExecution,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)

OptionalListGithubStepsWithReport: TypeAlias = OptionalResultWithReport[list[GithubStepInterface]]


@dataclass
class StepCapabilityGithubWorkflow(StepCapability):
    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return OptionalListGithubStepsWithReport.create_report(
            Report().append_error("StepCapabilityGithubWorkflow.to_githubwf need to be imlemented in subclasses")
        )


@dataclass
class OrchestratorVisitorGitHubWorkflowPreparation(OrchestratorVisitorBase):
    wf_job: JobOrchestratorMatrixExecution
    context: JobOrchestratorMatrixExecutionContext

    def init_visit(self) -> None:
        pass

    def end_visit(self, visit_complete: bool) -> None:
        pass

    def begin_phase(self, phase: Phase) -> None:
        pass

    def end_phase(self, phase_complete: bool) -> None:
        pass

    def visit_step(self, step: StepBase, reporter_sink: ReporterSinkBase) -> Report:
        capability = step.get_capability(StepCapabilityGithubWorkflow)
        if capability is None:
            return Report().append_info(f"skip step {step.name} because it does not support github workflow")
        steps_and_report = capability.to_githubwf(self.context, reporter_sink)
        if steps_and_report.result is not None:
            self.wf_job.steps += steps_and_report.result
        return steps_and_report.report
