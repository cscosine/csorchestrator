from dataclasses import dataclass
from pathlib import Path

import pytest

from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    GeneratorWithType,
)
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription
from csorchestrator.domain.orchestrator.step_base import StepExtra
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.validate_and_execute import create_os_and_path
from csorchestrator.frontend.reporters.reporter_sink_dummy import ReporterSinkDummy
from csorchestrator.frontend.step.step_get_repository import (
    StepGetRepositoryExtraAccessToken,
    StepGetRepositoryExtraDepthOne,
    StepGetRepositoryGitHub,
    execute_step_get_repository,
    validate_step_get_repository,
)
from tests.csorchestrator.repo_test_data_config import RepoTestData


@dataclass
class StepGetRepositoryExtraCustom(StepExtra):
    value: int


@dataclass
class StepGetRepositoryExtraNotUsed(StepExtra):
    pass


def test_step_get_repository():
    s = StepGetRepositoryGitHub(
        name="get repo",
        description="get repo desc",
        target_directory="dir",
        repo_url_parts=RepoUrlParts(
            StepGetRepositoryGitHub.GITHUB_BASE_URL_SSH,
            repo_org="cscosine",
            repo_name="myrepo",
        ),
        repo_ref="main",
    )
    s.add_extra(StepGetRepositoryExtraAccessToken(token_name="THE_TOKEN")).add_extra(StepGetRepositoryExtraCustom(25))

    assert s.get_extra(StepExtra) is None
    assert s.get_extra(StepGetRepositoryExtraNotUsed) is None

    token_extra = s.get_extra(StepGetRepositoryExtraAccessToken)
    assert token_extra is not None
    assert token_extra.token_name == "THE_TOKEN"

    custom_extra = s.get_extra(StepGetRepositoryExtraCustom)
    assert custom_extra is not None
    assert custom_extra.value == 25

    # substitute
    s.add_extra(StepGetRepositoryExtraCustom(52))
    custom_extra = s.get_extra(StepGetRepositoryExtraCustom)
    assert custom_extra is not None
    assert custom_extra.value == 52


def test_validate_step_get_repository() -> None:
    s = StepGetRepositoryGitHub(
        name="get repo",
        description="get repo desc",
        target_directory="../dir",
        repo_url_parts=RepoUrlParts(
            StepGetRepositoryGitHub.GITHUB_BASE_URL_SSH,
            repo_org="cscosine",
            repo_name="myrepo",
        ),
        repo_ref="main",
    )

    report = validate_step_get_repository(s)
    assert report.has_errors()
    assert "Invalid target_directory" in report.errors[0]

    s.target_directory = "dir"
    report = validate_step_get_repository(s)
    assert not report.has_errors()


def test_resolved_target_directory_path() -> None:
    s = StepGetRepositoryGitHub(
        name="get repo",
        description="get repo desc",
        target_directory="dir/subdir/..",
        repo_url_parts=RepoUrlParts(
            StepGetRepositoryGitHub.GITHUB_BASE_URL_SSH,
            repo_org="cscosine",
            repo_name="myrepo",
        ),
        repo_ref="main",
    )

    target_directory_path = s.resolved_target_directory_path()
    assert str(target_directory_path.name) == "dir"


def test_step_get_repository_extra_depth_one() -> None:
    s = StepGetRepositoryGitHub(
        name="get repo",
        description="get repo desc",
        target_directory="dir/subdir/..",
        repo_url_parts=RepoUrlParts(
            StepGetRepositoryGitHub.GITHUB_BASE_URL_SSH,
            repo_org="cscosine",
            repo_name="myrepo",
        ),
        repo_ref="main",
    )

    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(s)
    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(s)

    s.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=False, on_github_action_checkout=False))
    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(s)
    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(s)

    s.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=False))
    assert StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(s)
    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(s)

    s.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=False, on_github_action_checkout=True))
    assert not StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(s)
    assert StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(s)

    s.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))
    assert StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(s)
    assert StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(s)


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
@pytest.mark.parametrize(
    "repo_ref",
    [RepoTestData().main_branch, RepoTestData().dev_branch, RepoTestData().initial_commit_sha, RepoTestData().tag],
)
def test_execute_step_get_repository_success(
    tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool, repo_ref: str
) -> None:
    cfg = RepoTestData()

    step = StepGetRepositoryGitHub(
        name="get test repo",
        description="get test repo desc",
        target_directory=cfg.destination_folder,
        repo_url_parts=repo_url,
        repo_ref=repo_ref,
    )

    if depth_one:
        step.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))

    os_path_opt = create_os_and_path(tmp_path)
    assert os_path_opt.result is not None

    o = OrchestratorDescription(
        orchestrator_name="test_orchestrator",
        orchestrator_version="1.0.0",
        name_and_version_string="test_orchestrator-1.0.0",
    )

    context = ContextLocalExecution(
        orchestrator_description=o,
        script_folder_path=os_path_opt.result.path,
        base_folder_path=os_path_opt.result.path,
        os_architecture=os_path_opt.result.os_architecture,
        active_compiler_generator=ContextCompilerGenerator(
            Compiler.GCC, ContextCompilerGenerator.COMPILER_VERSION_DEFAULT, GeneratorWithType.MSVC_17_2022
        ),
        matrix_execution_id="1",
    )

    # execute the step for the first time, to clone the repo
    report = execute_step_get_repository(
        repo_step=step,
        context=context,
        reporter_sink=ReporterSinkDummy(),
    )

    assert not report.has_errors()
    assert report.has_info()
    assert "Clone from" in report.infos[0]

    # Verify actual disk state
    target_path = tmp_path / cfg.destination_folder
    status_file = target_path / cfg.file_to_verify
    assert status_file.exists(), f"File {cfg.file_to_verify} not found in cloned repo"

    expected_content = {
        cfg.main_branch: cfg.expected_content_main,
        cfg.dev_branch: cfg.expected_content_dev,
        cfg.initial_commit_sha: cfg.expected_content_initial,
        cfg.tag: cfg.expected_content_tag,
    }.get(repo_ref)
    assert status_file.read_text(encoding="utf-8").strip() == expected_content

    # and get a second time, to test the "update" logic
    report = execute_step_get_repository(
        repo_step=step,
        context=context,
        reporter_sink=ReporterSinkDummy(),
    )

    assert not report.has_errors()
    assert report.has_info()
    assert "Given target_directory exists, then try to update from" in report.infos[0]
    assert status_file.exists()
    assert status_file.read_text(encoding="utf-8").strip() == expected_content


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_execute_step_get_repository_update_fails(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    step = StepGetRepositoryGitHub(
        name="get test repo",
        description="get test repo desc",
        target_directory=cfg.destination_folder,
        repo_url_parts=repo_url,
        repo_ref=cfg.main_branch,
    )

    if depth_one:
        step.add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))

    os_path_opt = create_os_and_path(tmp_path)
    assert os_path_opt.result is not None

    o = OrchestratorDescription(
        orchestrator_name="test_orchestrator",
        orchestrator_version="1.0.0",
        name_and_version_string="test_orchestrator-1.0.0",
    )

    context = ContextLocalExecution(
        orchestrator_description=o,
        script_folder_path=os_path_opt.result.path,
        base_folder_path=os_path_opt.result.path,
        os_architecture=os_path_opt.result.os_architecture,
        active_compiler_generator=ContextCompilerGenerator(
            Compiler.GCC, ContextCompilerGenerator.COMPILER_VERSION_DEFAULT, GeneratorWithType.MSVC_17_2022
        ),
        matrix_execution_id="1",
    )

    # execute the step for the first time, to clone the repo
    report = execute_step_get_repository(
        repo_step=step,
        context=context,
        reporter_sink=ReporterSinkDummy(),
    )

    assert not report.has_errors()
    assert report.has_info()
    assert "Clone from" in report.infos[0]

    # and get a second time, to test the "update" logic and that it correctly detect errors
    step.repo_ref = cfg.dev_branch
    report = execute_step_get_repository(
        repo_step=step,
        context=context,
        reporter_sink=ReporterSinkDummy(),
    )

    assert report.has_errors()
    assert report.has_info()
    assert "Given target_directory exists, then try to update from" in report.infos[0]
    assert "Branch mismatch: local=main, expected=dev" in report.errors[0]
