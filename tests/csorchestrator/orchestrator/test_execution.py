from pathlib import Path

import pytest

from csorchestrator.application.factory.factory import create_orchestrator_factory_all_supported_cases
from csorchestrator.domain.execution.execution import ExecutionResult
from csorchestrator.domain.orchestrator.orchestrator_minimal_description import PhaseNameWithStepNames
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from csorchestrator.frontend.local_execution.validate_and_execute import validate_and_execute_orchestrator
from csorchestrator.frontend.reporters.orchestrator_executor_reporter_dummy import OrchestratorExecutorReporterDummy
from csorchestrator.frontend.step.step_get_repository import (
    StepGetRepositoryExtraDepthOne,
    StepGetRepositoryGitHub,
)
from tests.csorchestrator.repo_test_data_config import RepoTestData


@pytest.mark.slow
@pytest.mark.git
def test_validate_and_execute_orchestrator_success(tmp_path: Path, repo_url: RepoUrlParts) -> None:
    cfg = RepoTestData()

    orchestrator = create_orchestrator_factory_all_supported_cases("myName", "0.0.0", "exec-job")

    step = StepGetRepositoryGitHub(
        name=cfg.repo_name,
        description=cfg.repo_name + " description",
        target_directory=cfg.destination_folder,
        repo_url_parts=repo_url,
        repo_ref=cfg.main_branch,
    ).add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))

    orchestrator.add_phase(Phase(name="repos checkout").add_step(step))

    er: ExecutionResult = validate_and_execute_orchestrator(
        orchestrator=orchestrator,
        script_folder_path=tmp_path,
        target_folder_path=tmp_path,
        reporter=OrchestratorExecutorReporterDummy(),
    )
    assert not er.report_pre_execution.has_errors()
    assert er.execution_description is not None
    assert er.execution_description.phases_and_steps == [
        PhaseNameWithStepNames(phase_name="repos checkout", step_names=[cfg.repo_name])
    ]
    assert er.is_execution_successful() is not None


def test_validate_and_execute_orchestrator_fail_pre_execution(tmp_path: Path) -> None:

    # create a file in the target folder path,
    # which cause the pre-execution validation to fail, since it expects a folder
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    orchestrator = create_orchestrator_factory_all_supported_cases("myName", "0.0.0", "exec-job")

    er: ExecutionResult = validate_and_execute_orchestrator(
        orchestrator=orchestrator,
        script_folder_path=tmp_path,
        target_folder_path=file_path,
        reporter=OrchestratorExecutorReporterDummy(),
    )

    assert er.report_pre_execution.has_errors()


def test_validate_and_execute_orchestrator_fail_validation(tmp_path: Path, repo_url: RepoUrlParts) -> None:
    cfg = RepoTestData()

    orchestrator = create_orchestrator_factory_all_supported_cases("myName", "0.0.0", "exec-job")

    step = StepGetRepositoryGitHub(
        name=cfg.repo_name,
        description=cfg.repo_name + " description",
        target_directory=cfg.destination_folder,
        repo_url_parts=repo_url,
        repo_ref=cfg.main_branch,
    ).add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))

    p = Phase(name="repos checkout")
    # add the same step twice, which cause the validation to fail, since it expects unique step names per phase
    p.add_step(step)
    p.add_step(step)

    orchestrator.add_phase(p)

    er: ExecutionResult = validate_and_execute_orchestrator(
        orchestrator=orchestrator,
        script_folder_path=tmp_path,
        target_folder_path=tmp_path,
        reporter=OrchestratorExecutorReporterDummy(),
    )

    assert er.report_pre_execution.has_errors()
