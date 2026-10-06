# execution context
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from csorchestrator.domain.context.context_compiler_generator import ContextCompilerGenerator
from csorchestrator.domain.context.context_os_architecture import ContextOsArchitecture
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription


# base class for extra information that can be provided
class ContextLocalExecutionExtra:
    pass


ContextLocalExecutionExtraT = TypeVar("ContextLocalExecutionExtraT", bound=ContextLocalExecutionExtra)


# create it with create_local_context to ensure is a valid path pointint to an existing (eventually created) folder
@dataclass(frozen=True)
class ContextLocalExecution:
    orchestrator_description: OrchestratorDescription
    script_folder_path: Path
    base_folder_path: Path
    os_architecture: ContextOsArchitecture
    active_compiler_generator: ContextCompilerGenerator
    matrix_execution_id: str

    def get_active_os_architecture_compiler_generator(self) -> ContextOsArchitectureCompilerGenerator:
        return ContextOsArchitectureCompilerGenerator(self.os_architecture, self.active_compiler_generator)

    matrix_extras: dict[type, ContextLocalExecutionExtra] = field(
        default_factory=dict,
        kw_only=True,
    )

    # while matrix_extra is used to manage information across the execution
    # of multiple steps on the same matrix (e.g. to manage execution of steps with StepExecuteOnlyOncePerMatrix)
    def add_matrix_extra(
        self,
        extra: ContextLocalExecutionExtra,
    ) -> "ContextLocalExecution":
        key = type(extra)
        self.matrix_extras[key] = extra
        return self

    def remove_matrix_extra(
        self,
        key: type[ContextLocalExecutionExtraT],
    ) -> "ContextLocalExecution":
        self.matrix_extras.pop(key, None)  # no exception if not exists
        return self

    def get_matrix_extra(self, t: type[ContextLocalExecutionExtraT]) -> ContextLocalExecutionExtraT | None:
        extra = self.matrix_extras.get(t)
        return extra if isinstance(extra, t) else None
