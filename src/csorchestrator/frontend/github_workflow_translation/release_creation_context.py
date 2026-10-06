from dataclasses import dataclass
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription


@dataclass(frozen=True)
class ReleaseCreationContext:
    orchestrator_description: OrchestratorDescription
    matrix_list: list[ContextOsArchitectureCompilerGenerator]
    script_folder_path: Path
