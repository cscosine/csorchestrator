from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, field

from csorchestrator.domain.orchestrator.orchestrator_minimal_description import (
    OrchestratorExecutorMinimalDescription,
    PhaseNameWithStepNames,
)
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.domain.orchestrator.workflow_config import WorkflowConfig


# TODO support capabilities here to be more generic?
@dataclass
class MatrixExecutionBase(ABC):
    name: str

    def to_list_string_description(self) -> list[str]:
        return []


@dataclass
class OrchestratorDescription:
    orchestrator_name: str
    orchestrator_version: str
    name_and_version_string: str


@dataclass
class Orchestrator:
    # - create phase (e.g. setup / config / build)
    # per each phase allows to add
    #   - run custom command
    #   - get precompiled lib
    #   - add_repository
    #   - add local folder as src
    #   - run cmake workflow / individual steps (config / build / test / install)

    name: str
    version: str
    execution_matrix: MatrixExecutionBase
    phases: list[Phase] = field(default_factory=list)
    wf_config: WorkflowConfig | None = None

    def create_orchestrator_description(self) -> OrchestratorDescription:
        return OrchestratorDescription(
            orchestrator_name=self.name,
            orchestrator_version=self.version,
            name_and_version_string=self.name_version_to_string(),
        )

    @classmethod
    def compose_name_version_to_string(cls, name: str, version: str) -> str:
        return f"{name}-{version}"

    def name_version_to_string(self) -> str:
        return Orchestrator.compose_name_version_to_string(self.name, self.version)

    def add_phase(self, phase: Phase) -> "Orchestrator":
        self.phases.append(phase)
        return self

    def create_phase(self, phase_name: str) -> Phase:
        phase = Phase(phase_name)
        self.phases.append(phase)
        return phase

    def append(self, other: "Orchestrator", prefix: str = "") -> "Orchestrator":
        """Append all phases of ``other`` to this orchestrator.

        Phase names are unique within an orchestrator and step names are
        unique within a phase (enforced by the orchestrator validation). When
        ``other`` was filled by helpers that may emit phase/step names already
        present here (e.g. the same precompiled library downloaded once per
        providing release), pass ``prefix`` to namespace every appended phase
        and step name.

        The phases are deep-copied, so ``other`` is left untouched and can be
        appended multiple times with different prefixes.
        """
        for phase in other.phases:
            copied_phase = deepcopy(phase)
            if prefix:
                copied_phase.name = f"{prefix}{copied_phase.name}"
                for step in copied_phase.steps:
                    step.name = f"{prefix}{step.name}"
            self.add_phase(copied_phase)
        return self

    def extract_minimal_description(self) -> OrchestratorExecutorMinimalDescription:
        ret = OrchestratorExecutorMinimalDescription(name=self.name, version=self.version)
        for phase in self.phases:
            phase_desc = PhaseNameWithStepNames(phase.name)
            for step in phase.steps:
                phase_desc.step_names.append(step.name)
            ret.phases_and_steps.append(phase_desc)
            ret.matrix_description = self.execution_matrix.to_list_string_description()
        return ret
