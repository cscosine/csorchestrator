from pathlib import Path
from typing import Final

from csorchestrator.application.recipes.repos_config import (
    RepoRefBuildPublishConfigDict,
    ReposBuildConfigDict,
    ReposRefDict,
    extract_build_config_dict,
    extract_repo_list_build_non_none,
    extract_repo_ref_dict,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.local_execution.step_utils import StepExecuteOnlyOncePerMatrix
from csorchestrator.frontend.step.github_release_download import DownloadGithubFileEntry
from csorchestrator.frontend.step.step_cmake_command import StepCMakeWorkflow
from csorchestrator.frontend.step.step_create_archives import StepCreateArchives
from csorchestrator.frontend.step.step_deployments import StepCreateDeploymentArchives
from csorchestrator.frontend.step.step_get_release_archive_github import StepGetReleaseArchiveGithub
from csorchestrator.frontend.step.step_get_repository import (
    StepGetRepositoryExtraAccessToken,
    StepGetRepositoryExtraDepthOne,
    StepGetRepositoryGitHub,
    StepGetRepositoryGitHubSelf,
)
from csorchestrator.frontend.step.step_get_versions_from_cmake_config_package_version import (
    StepGetVersionsFromCMakeConfigPackageVersion,
)
from csorchestrator.frontend.step.step_upload_artifacts import (
    StepUploadArtifacts,
)
from csorchestrator.portable.package_version import CMakeConfigPackageVersionGrep, PackageVersion


class _All:
    pass


ALL: Final = _All()


def checkout_repos(
    orchestrator: Orchestrator,
    base_target_dir: Path,
    checkout_phase_name: str = "Repos Update",
    repo_ref_dict: ReposRefDict | None = None,
    checkout_self: bool = True,
    repo_access_token: str | None = None,
    release_archive_list: list[DownloadGithubFileEntry] | None = None,
) -> None:
    if repo_ref_dict is None:
        repo_ref_dict = {}

    if release_archive_list is None:
        release_archive_list = []

    p = orchestrator.create_phase(checkout_phase_name)

    # checkout myself for github actions
    if checkout_self:
        p.add_step(
            StepGetRepositoryGitHubSelf(
                name="Repo git self-checkout",
                description="Checkout self repository",
            )
        )

    # release archives (e.g. csCMake), extracted into base_target_dir
    for archive in release_archive_list:
        p.add_step(
            StepGetReleaseArchiveGithub(
                name=f"{archive.git_repo} {archive.tag} release",
                description=f"Download and extract {archive.asset_filename} of {archive.org}/{archive.git_repo}",
                archive=archive,
                extract_dir=base_target_dir.as_posix(),
            ).add_extra(StepExecuteOnlyOncePerMatrix())
        )

    for repo, repo_ref in repo_ref_dict.items():
        s = (
            StepGetRepositoryGitHub(
                name=f"{repo} Git clone/pull-ff",
                description=f"Clone or pull-ff {repo} description",
                target_directory=(base_target_dir / repo).as_posix(),
                repo_url_parts=RepoUrlParts(
                    repo_base_url=StepGetRepositoryGitHub.GITHUB_BASE_URL_SSH,
                    repo_org="cscosine",
                    repo_name=repo + ".git",
                ),
                repo_ref=repo_ref,
            )
            .add_extra(
                StepGetRepositoryExtraDepthOne(
                    on_local_checkout=False,
                    on_github_action_checkout=True,
                )
            )
            .add_extra(StepExecuteOnlyOncePerMatrix())
        )

        if repo_access_token is not None:
            s.add_extra(StepGetRepositoryExtraAccessToken(repo_access_token))

        p.add_step(s)


def build_repos(
    orchestrator: Orchestrator,
    base_target_dir: Path,
    build_phase_name: str = "Configure-Build-Test-Install",
    repo_build_config_dict: ReposBuildConfigDict | None = None,
    build_self: BuildConfig | None = None,
) -> None:
    if repo_build_config_dict is None:
        repo_build_config_dict = {}

    p = orchestrator.create_phase(build_phase_name)

    if build_self is not None:
        p.add_step(
            StepCMakeWorkflow(
                name="./ CMake Workflow",
                description="CMake workflow for ./",
                source_dir=Path("./").as_posix(),
                config=build_self,
            )
        )

    for repo, build_config in repo_build_config_dict.items():
        if build_config is not None:
            p.add_step(
                StepCMakeWorkflow(
                    name=f"{repo} CMake Workflow",
                    description=f"CMake workflow for {repo} with config: {build_config}",
                    source_dir=(base_target_dir / repo).as_posix(),
                    config=build_config,
                )
            )


def create_and_upload_artifacts(
    orchestrator: Orchestrator,
    base_install_dir: Path,
    create_artifact_phase_name: str = "Create and Upload Artifacts",
    repos_with_build_list: list[str] | None = None,
    repos_auto_search_list: list[str] | _All | None = ALL,
    repos_config_file_list: list[CMakeConfigPackageVersionGrep] | None = None,
    repos_version_list: list[PackageVersion] | None = None,
) -> None:
    if repos_with_build_list is None:
        repos_with_build_list = []

    p = orchestrator.create_phase(create_artifact_phase_name)

    repos_auto_search_list_value: list[str] = []
    if isinstance(repos_auto_search_list, _All):
        repos_auto_search_list_value = repos_with_build_list
    elif repos_auto_search_list is not None:
        repos_auto_search_list_value = repos_auto_search_list

    repos_config_file_list_value: list[CMakeConfigPackageVersionGrep] = []
    if repos_config_file_list is not None:
        repos_config_file_list_value = repos_config_file_list

    # repos_version: list[PackageVersion] | _All | None = (None,)
    repos_version_list_value: list[PackageVersion] = []
    if repos_version_list is not None:
        repos_version_list_value = repos_version_list

    p.add_step(
        StepGetVersionsFromCMakeConfigPackageVersion(
            name="Get Versions",
            description="Get Versions for all libs",
            repos_auto_search_list=repos_auto_search_list_value,
            repos_config_file_list=repos_config_file_list_value,
            repos_version=repos_version_list_value,
            base_install_dir=base_install_dir,
        )
    )

    p.add_step(
        StepCreateArchives(
            name="Create Archives",
            description="Create archives with libs and versions",
            base_install_dir=base_install_dir,
        )  # .add_extra(StepSkipExecutionOnLocal())
    )

    p.add_step(
        StepUploadArtifacts(
            name="Upload Artifacts",
            description="Upload Artifacts with libs and versions",
            base_install_dir=base_install_dir,
        )
    )


def create_and_upload_deployments(
    orchestrator: Orchestrator,
    base_build_dir: Path,
    build_config: BuildConfig,
    output_dir: Path,
    phase_name: str = "Create and Upload Deployments",
) -> None:
    """Archive the deployments (csCMake ``cs_deployment``) the install of the builds made, for the configurations of
    ``build_config`` (the one of ``build_repos``), in ``output_dir``; in GitHub, uploaded as artifacts (attached to the
    release by the release job)."""
    p = orchestrator.create_phase(phase_name)
    p.add_step(
        StepCreateDeploymentArchives(
            name="Create Deployment Archives",
            description="Archive the deployments made by the install",
            base_build_dir=base_build_dir,
            build_config=build_config,
            output_dir=output_dir,
        )
    )


def checkout_build_and_archive_repos(
    orchestrator: Orchestrator,
    base_target_dir: Path,
    base_install_dir: Path,
    checkout_phase_name: str = "Repos Update",
    build_phase_name: str = "Configure-Build-Test-Install",
    create_artifact_phase_name: str = "Create and Upload Artifacts",
    repo_ref_build_publish_config_dict: RepoRefBuildPublishConfigDict | None = None,
    checkout_self: bool = True,
    build_self: BuildConfig | None = None,
    repo_access_token: str | None = None,
    repos_auto_search_list: list[str] | _All | None = ALL,
    repos_config_file_list: list[CMakeConfigPackageVersionGrep] | None = None,
    repos_version_list: list[PackageVersion] | None = None,
    release_archive_list: list[DownloadGithubFileEntry] | None = None,
) -> None:
    if repo_ref_build_publish_config_dict is None:
        repo_ref_build_publish_config_dict = {}

    checkout_repos(
        orchestrator=orchestrator,
        base_target_dir=base_target_dir,
        checkout_phase_name=checkout_phase_name,
        repo_ref_dict=extract_repo_ref_dict(repo_ref_build_publish_config_dict),
        checkout_self=checkout_self,
        repo_access_token=repo_access_token,
        release_archive_list=release_archive_list,
    )

    build_repos(
        orchestrator=orchestrator,
        base_target_dir=base_target_dir,
        build_phase_name=build_phase_name,
        repo_build_config_dict=extract_build_config_dict(repo_ref_build_publish_config_dict),
        build_self=build_self,
    )

    create_and_upload_artifacts(
        orchestrator=orchestrator,
        base_install_dir=base_install_dir,
        create_artifact_phase_name=create_artifact_phase_name,
        repos_with_build_list=extract_repo_list_build_non_none(
            extract_build_config_dict(repo_ref_build_publish_config_dict)
        ),
        repos_auto_search_list=repos_auto_search_list,
        repos_config_file_list=repos_config_file_list,
        repos_version_list=repos_version_list,
    )
