from pathlib import Path

from csorchestrator.application.factory.factory import create_orchestrator_factory_all_supported_cases
from csorchestrator.application.recipes.checkout_build import ALL, _All, checkout_build_and_archive_repos
from csorchestrator.application.recipes.repos_config import (
    RepoRefBuildPublishConfigDict,
    ReposPublishConfigDict,
    extract_repo_publish_config_dict,
)
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    ExecutionMatrixOsArchCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.workflow_config import Cron, DayOfWeek, WorkflowConfig, WorkflowTrigger
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.step.release_creation import ReleaseCreationOnTagConfig
from csorchestrator.portable.package_version import CMakeConfigPackageVersionGrep, PackageVersion


def create_default_execution_matrix(
    matrix_list: list[ContextOsArchitectureCompilerGenerator],
    execution_matrix_name: str = "orchestrator-matrix",
) -> ExecutionMatrixOsArchCompilerGenerator:
    em = ExecutionMatrixOsArchCompilerGenerator(execution_matrix_name)

    em.os_architecture_compiler_generator_list = matrix_list

    return em


def create_default_orchestrator_and_default_checkout_build_upload(
    name: str,
    version: str,
    base_target_dir: Path,
    base_install_dir: Path,
    repo_ref_build_publish_config_dict: RepoRefBuildPublishConfigDict | None = None,
    execution_matrix_name: str = "orchestrator-matrix",
    on_push_branches: list[str] | None = None,
    on_pull_request_branches: list[str] | None = None,
    on_push_tags: list[str] | None = None,
    schedule: Cron | None = None,
    artifacts_dir: str = "artifacts",
    populate_default_matrix: bool = True,
    additional_files_list: list[Path] | None = None,
    output_bundle_file_name: Path | None = None,
    checkout_phase_name: str = "Repos Update",
    build_phase_name: str = "Configure-Build-Test-Install",
    create_artifact_phase_name: str = "Create and Upload Artifacts",
    checkout_self: bool = True,
    build_self: BuildConfig | None = None,
    repo_access_token: str | None = None,
    repos_auto_search_list: list[str] | _All | None = ALL,
    repos_config_file_list: list[CMakeConfigPackageVersionGrep] | None = None,
    repos_version_list: list[PackageVersion] | None = None,
) -> Orchestrator:
    if repo_ref_build_publish_config_dict is None:
        repo_ref_build_publish_config_dict = {}

    o = create_default_orchestrator(
        name=name,
        version=version,
        base_install_dir=base_install_dir,
        repo_publish_config_dict=extract_repo_publish_config_dict(repo_ref_build_publish_config_dict),
        execution_matrix_name=execution_matrix_name,
        on_push_branches=on_push_branches,
        on_pull_request_branches=on_pull_request_branches,
        on_push_tags=on_push_tags,
        schedule=schedule,
        artifacts_dir=artifacts_dir,
        populate_default_matrix=populate_default_matrix,
        additional_files_list=additional_files_list,
        output_bundle_file_name=output_bundle_file_name,
    )

    checkout_build_and_archive_repos(
        orchestrator=o,
        base_target_dir=base_target_dir,
        base_install_dir=base_install_dir,
        checkout_phase_name=checkout_phase_name,
        build_phase_name=build_phase_name,
        create_artifact_phase_name=create_artifact_phase_name,
        repo_ref_build_publish_config_dict=repo_ref_build_publish_config_dict,
        checkout_self=checkout_self,
        build_self=build_self,
        repo_access_token=repo_access_token,
        repos_auto_search_list=repos_auto_search_list,
        repos_config_file_list=repos_config_file_list,
        repos_version_list=repos_version_list,
    )
    return o


def create_default_orchestrator(
    name: str,
    version: str,
    base_install_dir: Path,
    repo_publish_config_dict: ReposPublishConfigDict | None = None,
    execution_matrix_name: str = "orchestrator-matrix",
    on_push_branches: list[str] | None = None,
    on_pull_request_branches: list[str] | None = None,
    on_push_tags: list[str] | None = None,
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

    if on_pull_request_branches is None:
        on_pull_request_branches = ["main"]
    if on_push_branches is None:
        on_push_branches = ["main", "dev"]
    if on_push_tags is None:
        on_push_tags = ["v*.*.*"]

    if repo_publish_config_dict is None:
        repo_publish_config_dict = {}

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
            on_push_branches=on_push_branches,
            on_push_tags=on_push_tags,
            on_pull_request_branches=on_pull_request_branches,
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
