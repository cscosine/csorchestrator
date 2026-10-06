from dataclasses import dataclass
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture import ContextOsArchitecture
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription


@dataclass(frozen=True)
class ReleaseCreationContextLocalExecution:
    os_architecture_compiler_generator_list: list[ContextOsArchitectureCompilerGenerator]
    orchestrator_description: OrchestratorDescription
    os_architecture: ContextOsArchitecture
    base_path: Path
    script_folder_path: Path
