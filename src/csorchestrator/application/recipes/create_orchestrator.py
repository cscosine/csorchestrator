from pathlib import Path

from csorchestrator.application.factory.factory import create_orchestrator_factory_all_supported_cases
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    ExecutionMatrixOsArchCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.workflow_config import Cron, DayOfWeek, WorkflowConfig, WorkflowTrigger
from csorchestrator.frontend.step.release_creation import ReleaseCreationOnTagConfig


def create_default_execution_matrix(
    matrix_list: list[ContextOsArchitectureCompilerGenerator],
    execution_matrix_name: str = "orchestrator-matrix",
) -> ExecutionMatrixOsArchCompilerGenerator:
    em = ExecutionMatrixOsArchCompilerGenerator(execution_matrix_name)

    em.os_architecture_compiler_generator_list = matrix_list

    return em


def create_default_orchestrator(
    name: str,
    version: str,
    base_install_dir: Path,
    execution_matrix_name: str = "orchestrator-matrix",
    main_branch: str = "main",
    dev_branch: str = "dev",
    release_tag: str = "v*.*.*",
    schedule: Cron | None = None,
    artifacts_dir: str = "artifacts",
    populate_default_matrix: bool = True,
    additional_files_list: list[Path] | None = None,
    output_bundle_file_name: Path | None = None,
) -> Orchestrator:
    if schedule is None:
        schedule = Cron.weekly(DayOfWeek.MON, hour=3)

    if additional_files_list is None:
        additional_files_list = []

    o = create_orchestrator_factory_all_supported_cases(
        name=name,
        version=version,
        execution_matrix_name=execution_matrix_name,
        populate_default_matrix=populate_default_matrix,
    )

    if output_bundle_file_name is None:
        output_bundle_file_name = Path(o.create_orchestrator_description().name_and_version_string + "-bundle.tar.gz")

    o.wf_config = WorkflowConfig(
        trigger=WorkflowTrigger(
            on_push_branches=[main_branch, dev_branch],
            on_push_tags=[release_tag],
            on_pull_request_branches=[main_branch],
            on_dispatch=True,
            on_schedule=schedule,
        ),
        create_release_on_tag=ReleaseCreationOnTagConfig(
            name="release-from-artifacts",
            base_install_dir=base_install_dir,
            artifacts_dir=artifacts_dir,
            additional_files_list=additional_files_list,
            output_bundle_file_name=output_bundle_file_name,
        ),
    )

    return o
