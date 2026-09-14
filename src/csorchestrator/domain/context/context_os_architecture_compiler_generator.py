from dataclasses import dataclass, field

from csorchestrator.domain.context.context_compiler_generator import ContextCompilerGenerator
from csorchestrator.domain.context.context_os_architecture import ContextOsArchitecture
from csorchestrator.domain.orchestrator.orchestrator import MatrixExecutionBase

CSORCHESTRATOR_SCHEMA_VERSION = "csv1"


@dataclass
class ContextOsArchitectureCompilerGenerator:
    context_os_architecture: ContextOsArchitecture
    context_compiler_generator: ContextCompilerGenerator


@dataclass
class ExecutionMatrixOsArchCompilerGenerator(MatrixExecutionBase):
    os_architecture_compiler_generator_list: list[ContextOsArchitectureCompilerGenerator] = field(default_factory=list)
    fail_fast = False

    def to_list_string_description(self) -> list[str]:
        ret: list[str] = []
        for c in self.os_architecture_compiler_generator_list:
            ret.append(create_context_os_architecture_compiler_generator_string(c))
        return ret


def create_context_os_architecture_compiler_generator_string_from_components(
    os: str,
    os_version: str,
    architecture: str,
    architecture_variant: str,
    compiler: str,
    compiler_version: str,
    build_generator: str,
) -> str:
    parts: list[str] = []
    parts.append(CSORCHESTRATOR_SCHEMA_VERSION.lower())
    parts.append(os.lower())
    parts.append(os_version.lower())
    parts.append(architecture.lower())
    parts.append(architecture_variant.lower())
    parts.append(compiler.lower())
    parts.append(compiler_version.lower())
    parts.append(build_generator.lower())
    return "-".join(parts)


def create_context_os_architecture_compiler_generator_string(
    context_os_architecture_generator: ContextOsArchitectureCompilerGenerator,
) -> str:
    """
    Creates canonical CS orchestrator ID.
    """

    context_os_architecture = context_os_architecture_generator.context_os_architecture
    context_compiler_generator = context_os_architecture_generator.context_compiler_generator

    return create_context_os_architecture_compiler_generator_string_from_components(
        context_os_architecture.os.value.lower(),
        context_os_architecture.os_version.lower(),
        context_os_architecture.architecture.value.lower(),
        context_os_architecture.architecture_variant.lower(),
        context_compiler_generator.compiler_family.value.lower(),
        context_compiler_generator.compiler_version.lower(),
        context_compiler_generator.build_generator.generator.value.lower(),
    )
