from dataclasses import dataclass

from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_matrix_execution import (
    MatrixOsArchCompilerGeneratorRunnerEntryInclude,
)


@dataclass(frozen=True)
class JobOrchestratorMatrixExecutionContext:
    orchestrator_description: OrchestratorDescription
    matrix_includes: list[MatrixOsArchCompilerGeneratorRunnerEntryInclude]
