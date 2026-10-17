import importlib
import os
import tarfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias
from urllib import request
from urllib.error import HTTPError, URLError

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
    compose_mapping_function,
    create_github_release_download_url,
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

    def create_manifest_filename(self) -> str:
        return create_manifest_filename(self.project_name, self.project_version)

    # TODO for private repo, will need to use API url and a api request to download, using a token,
    # with keyring in local and token in github


ProviderNameLibsList: TypeAlias = dict[str, list[str]]


def extract_provider_names(providers: list[ManifestGithub]) -> list[str]:
    ret: list[str] = []
    for p in providers:
        ret.append(p.project_name)
    return ret


# dict external lib provider name -> its dependencies
# {
#   "third_part_libs" :
#     {
#       "myLib": ["third_part_lib_base"],
#       "myOtherLib": ["third_part_lib_other"],
#     },
#   "gui_lib":
#     {
#       "myLib": ["gui_base_lib"]
#       "myOtherLib": ["gui_other_lib"],
#     }
#   }


def fill_in_providers_in_dependencies(
    dependencies: dict[str, dict[str, list[str]]], provider_names: list[str]
) -> dict[str, dict[str, list[str]]]:
    ret = deepcopy(dependencies)
    for p in provider_names:
        if p not in dependencies:
            ret[p] = {}
    return ret


# dict[str, list[str]]
# dict lib name -> its dependencies
# {"myLib" : ["coreLib", "baseLib"], "myOtherLib" : ["myOtherLib"]}


def fill_in_libraries_in_dependecies(
    dependencies: dict[str, list[str]], library_names: list[str]
) -> dict[str, list[str]]:
    ret = deepcopy(dependencies)
    for p in library_names:
        if p not in dependencies:
            ret[p] = []

    return ret


def fill_in_providers_and_libs_in_dependencies(
    dependencies: dict[str, dict[str, list[str]]],
    provider_names: list[str],
    library_names: list[str],
) -> dict[str, dict[str, list[str]]]:
    dependencies = fill_in_providers_in_dependencies(dependencies, provider_names)
    ret = deepcopy(dependencies)
    for p, libs in ret.items():
        libs = fill_in_libraries_in_dependecies(libs, library_names)
        ret[p] = libs
    return ret


def merge_library_dependencies(src: dict[str, list[str]], add: dict[str, list[str]]) -> dict[str, list[str]]:
    dst = deepcopy(src)
    for a, ll in add.items():
        for e in ll:
            if e not in dst[a]:
                dst[a].append(e)
    return dst


def merge_providers_dependencies(
    src: dict[str, dict[str, list[str]]], add: dict[str, dict[str, list[str]]]
) -> dict[str, dict[str, list[str]]]:
    dst = deepcopy(src)
    for p, lst in add.items():
        lst = merge_library_dependencies(lst, src[p])
        dst[p] = lst
    return dst


def fill_in_library_list(src: list[str] | None, default: list[str]) -> list[str]:
    if src is None:
        return deepcopy(default)
    return src


def extract_provider_libs_list(src: dict[str, dict[str, list[str]]], required_libs: list[str]) -> ProviderNameLibsList:
    ret: ProviderNameLibsList = {}
    for provider, deps in src.items():
        ret[provider] = []
        for src_lib, libs in deps.items():
            if src_lib in required_libs:
                ret[provider].extend(libs)
        ret[provider] = list(set(ret[provider]))
    return ret


# -------------

OptionalManifestPathWithReport: TypeAlias = OptionalResultWithReport[Path]


def create_steps_to_get_libs_from_manifest(
    orchestrator: Orchestrator,
    manifest_description: ManifestGithub,
    manifest_loaded: ReleaseManifest,
    base_libs_dir: Path,
    mapping_function: MappingFunction,
    phase_name: str,
    dev: bool,
    lib_name_list: list[str] | None = None,
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

    # collect lib name and versions declared in the manifest
    lib_versions: dict[str, set[str]] = {}
    for variant_entry in manifest_loaded.variants:
        for package_version in variant_entry.entries:
            lib_versions.setdefault(package_version.name, set()).add(package_version.version)

    # autofill the lib to select or check the provided list is valid
    selected_lib_names: list[str]
    if lib_name_list is None:
        selected_lib_names = sorted(lib_versions)
    else:
        selected_lib_names = lib_name_list
        for lib_name in selected_lib_names:
            if lib_name not in lib_versions:
                report.append_error(f"Library '{lib_name}' is not declared in the release manifest")

    # the library self dependencies
    dependencies_list: dict[str, list[str]] = {name: list(deps) for name, deps in manifest_loaded.dependencies.items()}
    dependencies_dev: dict[str, list[str]] = {
        name: list(deps) for name, deps in manifest_loaded.dependencies_dev.items()
    }

    if dev:
        # extend them if we are in dev mode
        dependencies_list = merge_library_dependencies(dependencies_list, dependencies_dev)

    # get transitive dependencies
    selected_lib_names = resolve_library_dependencies(selected_lib_names, dependencies_list)

    # check that lib version is unique across variants
    for lib_name in selected_lib_names:
        versions = sorted(lib_versions[lib_name])
        if len(versions) > 1:
            report.append_error(
                f"Library '{lib_name}' is declared with different versions per variant "
                f"({versions}); multiple versions of the same library are not supported "
                "at the moment"
            )

    if report.has_errors():
        return report

    # prepare steps to get the selected libs
    steps: list[StepGetPrecompiledLibGithub] = []
    for lib_name in selected_lib_names:
        versions = sorted(lib_versions[lib_name])
        assert len(versions) == 1  # guaranteed by the check above
        version = versions[0]

        headers_only = False
        if lib_name in manifest_loaded.headers_only_packages:
            headers_only = True

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
                lib_version=version,
                base_libs_dir=base_libs_dir,
                headers_only=headers_only,
                mapping_function=mapping_function,
            )
        )

    if phase_name is None:
        phase_name = f"get libraries from {manifest_description.project_name} {manifest_description.project_version}"

    p = orchestrator.create_phase(phase_name)
    for step in steps:
        p.add_step(step)

    return report


def create_manifest_filename(project_name: str, project_version: str) -> str:
    return ReleaseManifest.create_manifest_filename_from_project_name_and_version_string(
        Orchestrator.compose_name_version_to_string(project_name, project_version)
    )


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

    download_url = create_github_release_download_url(
        base_url=manifest_description.base_url,
        org=manifest_description.org,
        git_repo=manifest_description.git_repo,
        tag=manifest_description.release_tag,
        asset_filename=bundle_filename,
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
        return OptionalManifestPathWithReport.create_report(report)

    assert dir_creation_res.value is not None
    target_dir = dir_creation_res.value

    source_filename = Path(manifest_description.create_manifest_filename())
    target_filename = target_dir / source_filename

    download_url = create_github_release_download_url(
        base_url=manifest_description.base_url,
        org=manifest_description.org,
        git_repo=manifest_description.git_repo,
        tag=manifest_description.release_tag,
        asset_filename=source_filename,
    )
    report.append_info("download URL " + download_url + " to " + target_filename.as_posix())

    # download
    try:
        request.urlretrieve(download_url, target_filename)
    except HTTPError as e:
        report.append_error(f"HTTP error: {e.code} - {e.reason}")
        return OptionalManifestPathWithReport.create_report(report)

    except URLError as e:
        report.append_error(f"Network error: {e.reason}")
        return OptionalManifestPathWithReport.create_report(report)

    # Check file exists and is not empty
    if not os.path.exists(target_filename):
        report.append_error("Download failed: file does not exist")
        return OptionalManifestPathWithReport.create_report(report)

    if os.path.getsize(target_filename) == 0:
        report.append_error("Download failed: file is empty")
        return OptionalManifestPathWithReport.create_report(report)

    return OptionalManifestPathWithReport.create_result_and_report(target_filename, report)


def resolve_library_dependencies(
    lib_name_list: list[str],
    library_dependencies: dict[str, list[str]],
) -> list[str]:
    resolved: set[str] = set(lib_name_list)
    changed = True
    while changed:
        changed = False
        for lib in sorted(resolved):
            for dependency in library_dependencies.get(lib, ()):
                if dependency not in resolved:
                    resolved.add(dependency)
                    changed = True

    return sorted(resolved)


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


def resolve_libs_deps_and_install_dependencies(
    orchestrator: Orchestrator,
    base_libs_dir: Path,
    dependencies_config_path: Path,
    dev: bool,
    download_dependencies_manifest_and_bundle: bool,
    mapping_function: MappingFunction,
    required_libs: list[str] | None,  # none means all
    full_library_list: list[str],
    library_dependencies: dict[str, list[str]],
    library_dependencies_dev: dict[str, list[str]],
    external_provides_description: list[ManifestGithub],
    external_library_dependencies: dict[str, dict[str, list[str]]],
    external_library_dependencies_dev: dict[str, dict[str, list[str]]],
    provider_mapping_function: dict[str, str],
    phase_name_suffix: str,
) -> Report:
    report = Report()

    # convert to map with names
    external_providers_map: dict[str, ManifestGithub] = {}
    for m in external_provides_description:
        external_providers_map[m.project_name] = m

    # the library requested, completed with the known list
    required_libs = fill_in_library_list(required_libs, full_library_list)

    # the library self dependencies
    libs_self_dependencies = fill_in_libraries_in_dependecies(library_dependencies, full_library_list)
    if dev:
        # extend them if we are in dev mode
        libs_self_dependencies = merge_library_dependencies(
            fill_in_libraries_in_dependecies(library_dependencies, full_library_list),
            fill_in_libraries_in_dependecies(library_dependencies_dev, full_library_list),
        )

    # the library effectively requested, after resolving dependencies
    required_libs = resolve_library_dependencies(required_libs, libs_self_dependencies)

    # the indirect dependencies
    libs_external_dependencies = fill_in_providers_and_libs_in_dependencies(
        external_library_dependencies,
        extract_provider_names(external_provides_description),
        full_library_list,
    )
    if dev:
        libs_external_dependencies_dev = fill_in_providers_and_libs_in_dependencies(
            external_library_dependencies_dev,
            extract_provider_names(external_provides_description),
            full_library_list,
        )
        libs_external_dependencies = merge_providers_dependencies(
            libs_external_dependencies, libs_external_dependencies_dev
        )

    for _, provider_manifest_desc in external_providers_map.items():
        manifest_filename = Path(provider_manifest_desc.create_manifest_filename())

        if download_dependencies_manifest_and_bundle:
            manifest = download_manifest(provider_manifest_desc, dependencies_config_path)
            report.append_report(manifest.report)
            if manifest.result is not None:
                report.append_report(
                    download_manifest_bundle(
                        provider_manifest_desc,
                        ReleaseManifest.load_release_manifest(manifest.result),
                        dependencies_config_path,
                    )
                )
        else:
            report.append_warning(f"manifest {manifest_filename} download skipped")

    if report.has_errors():
        return report

    # for each provider, load the module it provides and run its autoinstall
    provider_libs_list = extract_provider_libs_list(libs_external_dependencies, required_libs)

    for provider, libs in provider_libs_list.items():
        module_name = f"{dependencies_config_path.as_posix()}.{provider}_config"

        provider_module = importlib.import_module(module_name)

        provider_manifest_desc = external_providers_map[provider]

        manifest_filename = Path(provider_manifest_desc.create_manifest_filename())

        provider_manifest_loaded = ReleaseManifest.load_release_manifest(
            dependencies_config_path.as_posix() / manifest_filename
        )

        provider_mapping_function_name = None
        if provider in provider_mapping_function:
            provider_mapping_function_name = provider_mapping_function[provider]

        composed_mapping = mapping_function
        if provider_mapping_function_name is not None:
            function = getattr(provider_module, provider_mapping_function_name)
            composed_mapping = compose_mapping_function(mapping_function, function)

        report.append_report(
            provider_module.auto_install_csorchestrator_managed_libraries(
                orchestrator=orchestrator,
                base_libs_dir=base_libs_dir,
                required_libs=libs,
                manifest_description=provider_manifest_desc,
                manifest_loaded=provider_manifest_loaded,
                dependencies_config_path=dependencies_config_path,
                mapping_function=composed_mapping,
                download_dependencies_manifest_and_bundle=download_dependencies_manifest_and_bundle,
                phase_name_suffix=phase_name_suffix + " " + provider,
            )
        )

    return report
