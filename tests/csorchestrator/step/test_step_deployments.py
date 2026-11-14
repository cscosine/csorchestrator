"""The deployments of a csCMake build: portable logic (find, archive, run) and the generated GitHub steps."""

import json
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    CreateGitHubRelease,
    StepGitHubUploadArtifacts,
    StepRunCommand,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.step.step_deployments import (
    StepCreateDeploymentArchives,
    StepRunDeployment,
    step_create_deployment_archives_to_githubwf,
    step_run_deployment_to_githubwf,
)
from csorchestrator.portable.deployments import (
    DeploymentArchives,
    DeploymentRun,
    cmake_configs_of_build_config,
    create_deployment_archives,
    find_deployment_folders,
    run_deployment,
    system_packages,
)

VARIANT = "csv1-linux-ubuntu24.04-x64-generic-gcc-default-ninja"


def _deployments(build_dir: Path, deploy_dir: Path, entries: list[tuple[str, str, list[str]]]) -> None:
    """Write cs-deployments.json in build_dir: (project, name, configs) entries, folders in deploy_dir."""
    data = {
        "version": 1,
        "build_dir": build_dir.as_posix(),
        "deployments": [
            {
                "name": name,
                "project": project,
                "configs": configs,
                "folders": {config: (deploy_dir / f"{name}-{config}").as_posix() for config in configs},
            }
            for project, name, configs in entries
        ],
    }
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "cs-deployments.json").write_text(json.dumps(data), encoding="utf-8")


def _deployment_folder(folder: Path) -> None:
    (folder / "bin").mkdir(parents=True)
    (folder / "bin" / "app").write_text("app\n", encoding="utf-8")
    (folder / "lib").mkdir()
    (folder / "lib" / "libx.so.1.0").write_text("x\n", encoding="utf-8")
    if sys.platform != "win32":  # a .zip on Windows: no symlinks
        (folder / "lib" / "libx.so.1").symlink_to("libx.so.1.0")


def test_cmake_configs_of_build_config() -> None:
    assert cmake_configs_of_build_config(BuildConfig.DEBUG_RELEASE.value) == ["Debug", "Release"]
    assert cmake_configs_of_build_config(BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID.value) == [
        "Debug",
        "Release",
        "RelWithDebInfo",
        "Paranoid",
    ]
    assert cmake_configs_of_build_config(BuildConfig.RELWITHDEBINFO.value) == ["RelWithDebInfo"]


def test_find_deployment_folders(tmp_path: Path) -> None:
    """The configurations listed and built; one file per single-config build folder, the same deployments once."""
    build, deploy = tmp_path / "build" / VARIANT, tmp_path / "deploy"
    for config in ("release", "relWithDebInfo"):
        _deployments(build / "app" / config, deploy, [("app", "demo", ["Release", "RelWithDebInfo"])])
    _deployment_folder(deploy / "demo-Release")
    _deployment_folder(deploy / "demo-RelWithDebInfo")

    folders, errors = find_deployment_folders(build, ["Debug", "Release", "RelWithDebInfo"])

    assert errors == []
    assert [(f.name, f.config) for f in folders] == [("demo", "RelWithDebInfo"), ("demo", "Release")]


def test_find_deployment_folders_fails_on_a_missing_folder(tmp_path: Path) -> None:
    build, deploy = tmp_path / "build", tmp_path / "deploy"
    _deployments(build, deploy, [("app", "demo", ["Release"])])

    _, errors = find_deployment_folders(build, ["Release"])

    assert len(errors) == 1
    assert "deployment demo (app, Release)" in errors[0] and "not found" in errors[0]


def test_find_deployment_folders_ignores_configurations_not_built(tmp_path: Path) -> None:
    build, deploy = tmp_path / "build", tmp_path / "deploy"
    _deployments(build, deploy, [("app", "demo", ["Release"])])

    folders, errors = find_deployment_folders(build, ["Debug"])

    assert (folders, errors) == ([], [])


def test_create_deployment_archives(tmp_path: Path) -> None:
    """One archive per deployment and configuration, the content under <base name>/, symlinks kept; the project of a
    deployment of another project in the name; zip on request."""
    build, deploy, out = tmp_path / "build", tmp_path / "deploy", tmp_path / "out"
    _deployments(build / "app", deploy, [("app", "demo", ["Release"])])
    _deployments(build / "dep", deploy, [("dep", "tool", ["Release"])])
    _deployment_folder(deploy / "demo-Release")
    _deployment_folder(deploy / "tool-Release")

    errors = create_deployment_archives(build, "debug-release", "app", "app-1.0.0", VARIANT, out, use_zip=False)

    assert errors == []
    assert sorted(p.name for p in out.iterdir()) == [
        f"app-1.0.0-{VARIANT}-demo-Release.tar.gz",
        f"app-1.0.0-{VARIANT}-dep-tool-Release.tar.gz",
    ]
    with tarfile.open(out / f"app-1.0.0-{VARIANT}-demo-Release.tar.gz") as archive:
        members = {m.name: m for m in archive.getmembers()}
    base = f"app-1.0.0-{VARIANT}-demo-Release"
    assert f"{base}/bin/app" in members
    if sys.platform != "win32":
        assert members[f"{base}/lib/libx.so.1"].issym()

    errors = create_deployment_archives(build / "app", "release", "app", "app-1.0.0", VARIANT, out, use_zip=True)

    assert errors == []
    with zipfile.ZipFile(out / f"{base}.zip") as archive:
        assert f"{base}/bin/app" in archive.namelist()


def test_create_deployment_archives_fails_on_a_missing_deployment(tmp_path: Path) -> None:
    build, deploy, out = tmp_path / "build", tmp_path / "deploy", tmp_path / "out"
    _deployments(build, deploy, [("app", "demo", ["Release"])])

    errors = create_deployment_archives(build, "release", "app", "app-1.0.0", VARIANT, out)

    assert len(errors) == 1 and "not found" in errors[0]
    assert not out.exists()


def test_system_packages(tmp_path: Path) -> None:
    (tmp_path / "system-requirements.txt").write_text(
        "# comment\napt install libc6 libxcb1\n#\nlibc.so.6 /lib/libc.so.6 libc6\n", encoding="utf-8"
    )
    assert system_packages(tmp_path) == ["libc6", "libxcb1"]
    assert system_packages(tmp_path / "none") == []


def _run(tmp_path: Path, code: str, archive: bool = True, **kwargs: object) -> list[str]:
    """Run python -c code {folder} on the deployment demo (Release) of a fake build in tmp_path, archived first."""
    build, deploy, archives = tmp_path / "build", tmp_path / "deploy", tmp_path / "archives"
    _deployments(build, deploy, [("app", "demo", ["Release"])])
    _deployment_folder(deploy / "demo-Release")
    if archive:
        assert create_deployment_archives(build, "release", "app", "app-1.0.0", VARIANT, archives) == []
    run = DeploymentRun(deployment="demo", command=[sys.executable, "-c", code, "{folder}"], **kwargs)  # type: ignore[arg-type]
    return run_deployment(build, "release", run, DeploymentArchives(archives, "app", "app-1.0.0", VARIANT))


def test_run_deployment_extracted_from_its_archive_with_a_clean_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """{folder}: the deployment extracted from its archive, elsewhere than its folder (symlinks kept, Linux and
    macOS); the environment of the caller not passed (clean_environment)."""
    monkeypatch.setenv("CSORCHESTRATOR_TEST_VARIABLE", "1")
    deploy = str((tmp_path / "deploy").resolve())
    symlink = "os.path.islink(folder + '/lib/libx.so.1')" if sys.platform != "win32" else "True"
    code = "import os, sys; from pathlib import Path; folder = sys.argv[1]; "
    code += f"sys.exit(0 if os.path.isfile(folder + '/bin/app') and {symlink} and "
    code += f"not str(Path(folder).resolve()).startswith({deploy!r}) and "
    code += "'CSORCHESTRATOR_TEST_VARIABLE' not in os.environ else 3)"

    assert _run(tmp_path, code) == []


def test_run_deployment_with_variables_set_on_top(tmp_path: Path) -> None:
    code = "import os, sys; sys.exit(0 if os.environ.get('QT_OPENGL') == 'software' else 3)"

    assert _run(tmp_path, code, environment={"QT_OPENGL": "software"}) == []


def test_run_deployment_fails_without_its_archive(tmp_path: Path) -> None:
    errors = _run(tmp_path, "import sys; sys.exit(0)", archive=False)

    assert len(errors) == 1
    assert "deployment demo (Release): no archive in" in errors[0]


def test_run_deployment_fails_on_another_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Another exit code fails; the files of the deployment logged."""
    errors = _run(tmp_path, "import sys; sys.exit(1)")

    assert errors == ["deployment demo (Release): exit code 1, expected 0"]
    out = capsys.readouterr().out
    assert "the files of the deployment" in out and "bin/app" in out
    assert _run(tmp_path / "expected", "import sys; sys.exit(1)", expect_exit_code=1) == []


def test_run_deployment_fails_on_a_timeout(tmp_path: Path) -> None:
    errors = _run(tmp_path, "import time; time.sleep(10)", timeout_seconds=0.5)

    assert errors == ["deployment demo (Release): still running after 0.5 s"]


def test_run_deployment_fails_on_an_unknown_deployment(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _deployments(build, tmp_path / "deploy", [])

    archives = DeploymentArchives(tmp_path / "archives", "app", "app-1.0.0", VARIANT)
    errors = run_deployment(build, "release", DeploymentRun(deployment="demo", command=["true"]), archives)

    assert errors == [f"deployment demo: not in the builds of {build} (release)"]


def _job() -> JobOrchestratorMatrixExecutionContext:
    description = OrchestratorDescription("app", "1.0.0", "app-1.0.0")
    return JobOrchestratorMatrixExecutionContext(orchestrator_description=description, matrix_includes=[])


def test_github_steps_of_the_archives() -> None:
    """A Python step running the portable code of csorchestratorsdk (valid Python), then the upload of the archives."""
    step = StepCreateDeploymentArchives(
        name="Create Deployment Archives",
        description="",
        base_build_dir=Path("workspace/build"),
        build_config=BuildConfig.DEBUG_RELEASE,
        output_dir=Path("workspace/deploy-archives"),
    )

    steps = step_create_deployment_archives_to_githubwf(step, _job()).result_or([])

    assert len(steps) == 2
    run, upload = steps
    assert isinstance(run, StepRunCommand) and isinstance(upload, StepGitHubUploadArtifacts)
    code = "\n".join(run.run)
    compile(code, "create_deployment_archives.py", "exec")
    assert "from csorchestratorsdk.portable.deployments import" in code
    assert "build_config = 'debug-release'" in code
    assert upload.with_path == ["workspace/deploy-archives/*.tar.gz", "workspace/deploy-archives/*.zip"]
    assert upload.with_name.startswith("app-1.0.0-") and upload.with_name.endswith("-deployments")


def test_github_step_of_a_run() -> None:
    step = StepRunDeployment(
        name="Smoke",
        description="",
        deployment="app",
        command={OS.LINUX: ["xvfb-run", "-a", "{folder}/bin/app", "--smoke"], OS.WINDOWS: ["{folder}/bin/app.exe"]},
        base_build_dir=Path("workspace/build"),
        build_config=BuildConfig.RELEASE,
        archives_dir=Path("workspace/deploy-archives"),
        install_system_requirements=True,
        environment={"QT_OPENGL": "software"},
    )

    steps = step_run_deployment_to_githubwf(step, _job()).result_or([])

    assert len(steps) == 1
    run = steps[0]
    assert isinstance(run, StepRunCommand)
    code = "\n".join(run.run)
    compile(code, "run_deployment.py", "exec")
    assert "'linux': ['xvfb-run', '-a', '{folder}/bin/app', '--smoke']" in code
    assert "'windows': ['{folder}/bin/app.exe']" in code
    assert "install_system_requirements = True" in code
    assert "environment = {'QT_OPENGL': 'software'}" in code


def test_the_release_attaches_the_zip_archives() -> None:
    files = CreateGitHubRelease(artifacts_folder="artifacts", if_str="true", additional_files_list=[]).to_dict()
    assert "artifacts/**/*.zip" in str(files["with"]["files"])
