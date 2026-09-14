import io
import shutil
import tarfile
from pathlib import Path
from urllib.error import URLError

from csorchestrator.application.factory.factory import (
    create_orchestrator_factory_all_supported_cases,
)
from csorchestrator.application.recipes.manifest_github import (
    ManifestGithub,
    create_steps_to_get_libs_from_manifest,
    download_manifest_bundle,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.frontend.step.step_get_precompiled_lib_github import (
    StepGetPrecompiledLibGithub,
)
from csorchestrator.portable.package_version import PackageVersion
from csorchestrator.portable.release_manifest import (
    ManifestVersionsEntry,
    ReleaseManifest,
)

PROJECT_NAME = "3rdPartyBaseLibs"
REPO_NAME = "3rdPartyBaseLibsRepo"
PROJECT_VERSION = "0.1.0"
PROJECT_TAG = "vX.X.X"
DEFAULT_PHASE_NAME = "get libraries from 3rdPartyBaseLibs0.1.0"


def _manifest_description() -> ManifestGithub:
    return ManifestGithub(
        base_url=StepGetPrecompiledLibGithub.GITHUB_BASE_URL_HTTPS,
        org="cscosine",
        git_repo=REPO_NAME,
        project_name=PROJECT_NAME,
        project_version=PROJECT_VERSION,
        release_tag=PROJECT_TAG,
    )


def _create_orchestrator() -> Orchestrator:
    return create_orchestrator_factory_all_supported_cases(
        name="test",
        version="0.1.0",
        execution_matrix_name="orchestrator-matrix",
        populate_default_matrix=False,
    )


def _release_manifest(
    pairs_per_variant: list[list[tuple[str, str]]],
) -> ReleaseManifest:
    return ReleaseManifest(
        project_name=PROJECT_NAME,
        project_version=PROJECT_VERSION,
        additional_files=[],
        output_bundle_file_name=None,
        variants=[
            ManifestVersionsEntry(
                variant=f"variant-{index}",
                entries=[PackageVersion(name, version) for name, version in pairs],
            )
            for index, pairs in enumerate(pairs_per_variant)
        ],
    )


def test_create_steps_to_get_libs_from_manifest_creates_one_step_per_lib_with_default_phase_name():
    manifest = _release_manifest(
        [
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
        ]
    )

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
    )

    assert not report.has_errors()
    assert [phase.name for phase in orchestrator.phases] == [DEFAULT_PHASE_NAME]

    steps = orchestrator.phases[0].steps
    assert [step.name for step in steps] == [
        "Get Precompiled Lib Catch2",
        "Get Precompiled Lib fmt",
    ]
    assert all(isinstance(step, StepGetPrecompiledLibGithub) for step in steps)

    catch2 = steps[0]
    fmt = steps[1]
    assert isinstance(catch2, StepGetPrecompiledLibGithub)
    assert isinstance(fmt, StepGetPrecompiledLibGithub)
    assert catch2.lib_name == "Catch2"
    assert catch2.lib_version == "3.10.0"
    assert catch2.project_tag == PROJECT_TAG
    assert catch2.org == "cscosine"
    assert catch2.project_name == PROJECT_NAME
    assert catch2.base_libs_dir == Path("workspace/libs")
    assert fmt.lib_name == "fmt"
    assert fmt.lib_version == "11.2.1"


def test_create_steps_to_get_libs_from_manifest_custom_phase_name():
    manifest = _release_manifest([[("fmt", "11.2.1")]])

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
        phase_name="get precompiled libs",
    )

    assert not report.has_errors()
    assert [phase.name for phase in orchestrator.phases] == ["get precompiled libs"]
    assert len(orchestrator.phases[0].steps) == 1


def test_create_steps_to_get_libs_from_manifest_errors_when_lib_has_multiple_versions():
    manifest = _release_manifest(
        [
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
            [("Catch2", "3.10.0"), ("fmt", "10.1.1")],
        ]
    )

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
    )

    assert report.has_errors()
    assert len(report.errors) == 1
    assert "fmt" in report.errors[0]
    assert "not supported at the moment" in report.errors[0]
    assert orchestrator.phases == []


def test_create_steps_to_get_libs_from_manifest_lib_declared_only_in_one_variant():
    manifest = _release_manifest(
        [
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
            [("Catch2", "3.10.0")],
        ]
    )

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
    )

    assert not report.has_errors()
    steps = orchestrator.phases[0].steps
    assert [step.name for step in steps] == [
        "Get Precompiled Lib Catch2",
        "Get Precompiled Lib fmt",
    ]


def test_create_steps_to_get_libs_from_manifest_empty_manifest_creates_empty_phase():
    manifest = _release_manifest([])

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
    )

    assert not report.has_errors()
    assert [phase.name for phase in orchestrator.phases] == [DEFAULT_PHASE_NAME]
    assert orchestrator.phases[0].steps == []


def test_create_steps_to_get_libs_from_manifest_subsample_with_lib_name_list():
    manifest = _release_manifest(
        [
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
            [("Catch2", "3.10.0"), ("fmt", "11.2.1")],
        ]
    )

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
        lib_name_list=["fmt"],
    )

    assert not report.has_errors()
    steps = orchestrator.phases[0].steps
    assert [step.name for step in steps] == ["Get Precompiled Lib fmt"]


def test_create_steps_to_get_libs_from_manifest_unknown_lib_in_list_errors():
    manifest = _release_manifest([[("fmt", "11.2.1")]])

    orchestrator = _create_orchestrator()
    report = create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=_manifest_description(),
        manifest_loaded=manifest,
        base_libs_dir=Path("workspace/libs"),
        lib_name_list=["fmt", "notALib"],
    )

    assert report.has_errors()
    assert len(report.errors) == 1
    assert "notALib" in report.errors[0]
    assert "not declared in the release manifest" in report.errors[0]
    assert orchestrator.phases == []


def _release_manifest_with_bundle(bundle_file_name: str | None) -> ReleaseManifest:
    return ReleaseManifest(
        project_name=PROJECT_NAME,
        project_version=PROJECT_VERSION,
        additional_files=["csBaseLibs/csorchestrator_config.py"],
        output_bundle_file_name=bundle_file_name,
        variants=[],
    )


def _create_bundle_tar_gz(path: Path) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        content = b"# config placeholder\n"
        info = tarfile.TarInfo("csBaseLibs/csorchestrator_config.py")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return path


def test_download_manifest_bundle_no_bundle_declared_does_nothing(tmp_path):
    manifest = _release_manifest_with_bundle(None)
    extract_folder = tmp_path / "libs"

    report = download_manifest_bundle(
        _manifest_description(),
        manifest,
        extract_folder,
    )

    assert not report.has_errors()
    assert not extract_folder.exists()


def test_download_manifest_bundle_downloads_and_extracts(tmp_path, monkeypatch):
    bundle_path = _create_bundle_tar_gz(tmp_path / "bundle.tar.gz")

    def fake_urlretrieve(url: str, filename: str) -> None:
        assert "3rdPartyBaseLibs-0.1.0-bundle.tar.gz" in url
        shutil.copyfile(bundle_path, filename)

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)

    manifest = _release_manifest_with_bundle("3rdPartyBaseLibs-0.1.0-bundle.tar.gz")
    extract_folder = tmp_path / "libs"

    report = download_manifest_bundle(
        _manifest_description(),
        manifest,
        extract_folder,
    )

    assert not report.has_errors()
    bundle_file = extract_folder / "3rdPartyBaseLibs-0.1.0-bundle.tar.gz"
    assert not bundle_file.exists()  # archive is removed after extraction
    extracted = extract_folder / "csBaseLibs/csorchestrator_config.py"
    assert extracted.is_file()
    assert extracted.read_text() == "# config placeholder\n"


def test_download_manifest_bundle_download_error_reported(tmp_path, monkeypatch):
    def fake_urlretrieve(url: str, filename: str) -> None:
        raise URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)

    manifest = _release_manifest_with_bundle("3rdPartyBaseLibs-0.1.0-bundle.tar.gz")
    extract_folder = tmp_path / "libs"

    report = download_manifest_bundle(
        _manifest_description(),
        manifest,
        extract_folder,
    )

    assert report.has_errors()
    assert len(report.errors) == 1
    assert "Network error" in report.errors[0]
    assert not (extract_folder / "3rdPartyBaseLibs-0.1.0-bundle.tar.gz").exists()
    assert extract_folder.exists()
