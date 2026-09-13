import os
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from csorchestrator.domain.context.context_os_architecture import (
    OS,
    UBUNTU_STRING_PREFIX,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.core.optional_result_with_report import (
    OptionalResultWithReport,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.foundation.file_system.directory import (
    ensure_directory_exists_or_create_and_is_usable,
)
from csorchestrator.frontend.local_execution.step_utils import (
    StepExecuteOnlyOn,
    StepExecuteOnlyOncePerMatrix,
)
from csorchestrator.frontend.step.step_custom_command import StepInstallAptPackages
from csorchestrator.frontend.step.step_get_precompiled_lib_github import (
    MappingFunction,
    StepGetPrecompiledLibGithub,
)
from csorchestrator.frontend.step.step_get_repository import StepGetRepositoryGitHub
from csorchestrator.portable.release_manifest import ReleaseManifest


@dataclass(frozen=True)
class ManifestGithub:
    base_url: str
    org: str
    git_repo: str
    project_name: str
    project_version: str
    release_tag: str

    GITHUB_BASE_URL_HTTPS: str = StepGetRepositoryGitHub.GITHUB_BASE_URL_HTTPS

    # TODO for private repo, will need to use API url and a api request to download, using a token,
    # with keyring in local and token in github


OptionalManifestPathWithReport: TypeAlias = OptionalResultWithReport[Path]


def create_steps_to_get_libs_from_manifest(
    orchestrator: Orchestrator,
    manifest_description: ManifestGithub,
    manifest_loaded: ReleaseManifest,
    base_libs_dir: Path,
    phase_name: str | None = None,
    lib_name_list: list[str] | None = None,
    mapping_function: MappingFunction | None = None,
) -> Report:
    """
    Add a phase with one StepGetPrecompiledLibGithub per selected library declared in the release manifest.

    If lib_name_list is None all libraries declared in the manifest are selected, otherwise only the
    libraries in the list are selected (subsample); a library in the list that is not declared in the
    manifest is reported as an error.

    A precompiled library is downloaded as a single archive per variant, so a library must have the same
    version in every variant it is declared in. The versions declared across all variants are collected
    and collapsed to a unique set; if a library is declared with more than one different version, an error
    is reported and no phase is created (multiple versions of the same library are not supported at the
    moment).
    """
    report = Report()

    lib_versions: dict[str, set[str]] = {}
    for variant_entry in manifest_loaded.variants:
        for package_version in variant_entry.entries:
            lib_versions.setdefault(package_version.name, set()).add(package_version.version)

    selected_lib_names: list[str]
    if lib_name_list is None:
        selected_lib_names = sorted(lib_versions)
    else:
        selected_lib_names = lib_name_list
        for lib_name in selected_lib_names:
            if lib_name not in lib_versions:
                report.append_error(f"Library '{lib_name}' is not declared in the release manifest")

    steps: list[StepGetPrecompiledLibGithub] = []
    for lib_name in selected_lib_names:
        if lib_name not in lib_versions:
            continue
        versions = sorted(lib_versions[lib_name])
        if len(versions) > 1:
            report.append_error(
                f"Library '{lib_name}' is declared with different versions per variant "
                f"({versions}); multiple versions of the same library are not supported "
                "at the moment"
            )
            continue

        steps.append(
            StepGetPrecompiledLibGithub(
                name=f"Get Precompiled Lib {lib_name}",
                description=f"get precompiled lib {lib_name} from github release",
                base_url=manifest_description.base_url,
                org=manifest_description.org,
                git_repo=manifest_description.git_repo,
                project_name=manifest_description.project_name,
                project_version=manifest_description.project_version,
                project_tag=manifest_description.release_tag,
                lib_name=lib_name,
                lib_version=versions[0],
                base_libs_dir=base_libs_dir,
                mapping_function=mapping_function,
            )
        )

    if report.has_errors():
        return report

    if phase_name is None:
        phase_name = f"get libraries from {manifest_description.project_name}{manifest_description.project_version}"

    p = orchestrator.create_phase(phase_name)
    for step in steps:
        p.add_step(step)

    return report


def download_manifest_bundle(
    manifest_description: ManifestGithub,
    release_manifest: ReleaseManifest,
    extract_folder: Path,
) -> Report:
    """
    Download and extract the additional-files bundle declared in the release manifest (if any).

    The bundle archive is downloaded from the same GitHub release and stored in the same folder
    as the manifest (output_folder), then extracted under extract_folder, preserving the folder
    structure of its content. If the release manifest does not declare an output bundle file
    name, nothing is downloaded and no error is reported.
    """
    report = Report()

    bundle_file_name = release_manifest.output_bundle_file_name
    if bundle_file_name is None:
        report.append_info(
            f"No bundle file specified in the release manifest "
            f"{release_manifest.project_name}-{release_manifest.project_version}"
        )
        return report

    extract_creation_res = ensure_directory_exists_or_create_and_is_usable(extract_folder.resolve())
    if extract_creation_res.error is not None:
        report.append_error(extract_creation_res.error)
        return report

    assert extract_creation_res.value is not None
    extract_dir = extract_creation_res.value

    bundle_filename = Path(bundle_file_name).name
    target_filename = extract_dir / bundle_filename

    download_url = urljoin(
        manifest_description.base_url,
        "/".join(
            [
                manifest_description.org,
                manifest_description.git_repo,
                "releases",
                "download",
                manifest_description.release_tag,
                bundle_filename,
            ]
        ),
    )
    report.append_info("download URL " + download_url + " to " + target_filename.as_posix())

    try:
        request.urlretrieve(download_url, target_filename)
    except HTTPError as e:
        report.append_error(f"HTTP error: {e.code} - {e.reason}")
        return report

    except URLError as e:
        report.append_error(f"Network error: {e.reason}")
        return report

    # Check file exists and is not empty
    if not os.path.exists(target_filename):
        report.append_error("Download failed: file does not exist")
        return report

    if os.path.getsize(target_filename) == 0:
        report.append_error("Download failed: file is empty")
        return report

    if not tarfile.is_tarfile(target_filename):
        report.append_error("Downloaded bundle is not a valid tar archive")
        return report

    try:
        with tarfile.open(target_filename, "r:gz") as tar:
            tar.extractall(extract_dir)
    except tarfile.ReadError:
        report.append_error(f"Extraction failed: corrupted tar.gz file {target_filename}")
        return report

    # Delete archive
    os.remove(target_filename)

    return report


def download_manifest(manifest_description: ManifestGithub, output_folder: Path) -> OptionalManifestPathWithReport:
    report = Report()

    dir_creation_res = ensure_directory_exists_or_create_and_is_usable(output_folder.resolve())

    if dir_creation_res.error is not None:
        report.append_error(dir_creation_res.error)
        return OptionalManifestPathWithReport.createReport(report)

    assert dir_creation_res.value is not None
    target_dir = dir_creation_res.value

    # TODO not great to join with "-" here
    source_filename = (
        manifest_description.project_name
        + "-"
        + manifest_description.project_version
        + ReleaseManifest.CS_ORCHESTRATOR_MANIFEST_EXTENSION
    )
    target_filename = target_dir / source_filename

    download_url = urljoin(
        manifest_description.base_url,
        "/".join(
            [
                manifest_description.org,
                manifest_description.git_repo,
                "releases",
                "download",
                manifest_description.release_tag,
                source_filename,
            ]
        ),
    )
    report.append_info("download URL " + download_url + " to " + target_filename.as_posix())

    # download
    try:
        request.urlretrieve(download_url, target_filename)
    except HTTPError as e:
        report.append_error(f"HTTP error: {e.code} - {e.reason}")
        return OptionalManifestPathWithReport.createReport(report)

    except URLError as e:
        report.append_error(f"Network error: {e.reason}")
        return OptionalManifestPathWithReport.createReport(report)

    # Check file exists and is not empty
    if not os.path.exists(target_filename):
        report.append_error("Download failed: file does not exist")
        return OptionalManifestPathWithReport.createReport(report)

    if os.path.getsize(target_filename) == 0:
        report.append_error("Download failed: file is empty")
        return OptionalManifestPathWithReport.createReport(report)

    return OptionalManifestPathWithReport.createResultAndReport(target_filename, report)


def download_csorchestrator_managed_libraries(
    orchestrator: Orchestrator,
    base_url: str,
    org: str,
    git_repo: str,
    project_name: str,
    project_version: str,
    release_tag: str,
    base_libs_dir: Path,
    manifest_dest_folder: Path | None = None,
    bundle_dest_folder: Path | None = None,
    lib_name_list: list[str] | None = None,
    mapping_function: MappingFunction | None = None,
) -> Report:
    if manifest_dest_folder is None:
        manifest_dest_folder = Path("libs") / Path("manifests")

    if bundle_dest_folder is None:
        bundle_dest_folder = Path("libs")

    report = Report()

    manifest_description = ManifestGithub(
        base_url=base_url,
        org=org,
        git_repo=git_repo,
        project_name=project_name,
        project_version=project_version,
        release_tag=release_tag,
    )

    manifest_path_with_report = download_manifest(
        manifest_description,
        manifest_dest_folder,
    )
    report.append_report(manifest_path_with_report.report)

    if manifest_path_with_report.result is not None:
        manifest_loaded = ReleaseManifest.load_release_manifest(manifest_path_with_report.result)

        report.append_report(
            download_manifest_bundle(
                manifest_description,
                manifest_loaded,
                bundle_dest_folder,
            )
        )

        report.append_report(
            create_steps_to_get_libs_from_manifest(
                orchestrator=orchestrator,
                manifest_description=manifest_description,
                manifest_loaded=manifest_loaded,
                base_libs_dir=base_libs_dir,
                lib_name_list=lib_name_list,
                mapping_function=mapping_function,
            )
        )

    return report


def install_ubuntu_apt_packages(
    orchestrator: Orchestrator,
    packages: list[str],
    name: str = "install apt packages",
    description: str = "install apt packages if not already installed in the system",
    phase_name: str = "Install Requirements (Linux-Ubuntu)",
) -> None:

    p = orchestrator.create_phase(phase_name)
    p.add_step(
        StepInstallAptPackages(
            name=name,
            description=description,
            packages=packages,
            dry_run=False,
        )
        .add_extra(StepExecuteOnlyOncePerMatrix())
        .add_extra(StepExecuteOnlyOn(os=OS.LINUX, version_starts_with=UBUNTU_STRING_PREFIX))
    )
