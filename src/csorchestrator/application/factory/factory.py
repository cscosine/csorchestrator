from typing import TypeAlias

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ExecutionMatrixOsArchCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.core.optional_result_with_report import OptionalResultWithReport
from csorchestrator.frontend.cscmake_presets.supported_variants import get_supported_context_os_architecture_list


def create_orchestrator_factory_all_supported_cases(
    name: str, version: str, execution_matrix_name: str, populate_default_matrix: bool = True
) -> Orchestrator:

    em = ExecutionMatrixOsArchCompilerGenerator(execution_matrix_name)

    if populate_default_matrix:
        em.os_architecture_compiler_generator_list = get_supported_context_os_architecture_list()

    o = Orchestrator(
        name=name,
        version=version,
        execution_matrix=em,
    )

    return o


OptionalOrchestratorWithReport: TypeAlias = OptionalResultWithReport[Orchestrator]
