from pathlib import Path

import pytest

from csorchestrator.application.factory.factory import create_orchestrator_factory_all_supported_cases
from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    GeneratorWithType,
)
from csorchestrator.domain.orchestrator.orchestrator import OrchestratorDescription
from csorchestrator.domain.orchestrator.orchestrator_executor import (
    execute_orchestrator,
    executor_visit_reports_has_any_error,
)
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import OrchestratorVisitorLocalExecutor
from csorchestrator.frontend.local_execution.validate_and_execute import create_os_and_path
from csorchestrator.frontend.reporters.orchestrator_executor_reporter_dummy import OrchestratorExecutorReporterDummy
from csorchestrator.frontend.step.step_get_repository import StepGetRepositoryExtraDepthOne, StepGetRepositoryGitHub
from csorchestrator.frontend.validation.validated_orchestrator import create_validated_orchestrator
from tests.csorchestrator.repo_test_data_config import RepoTestData


@pytest.mark.slow
@pytest.mark.git
def test_orchestrator_visitor_local_executor_succeed(tmp_path: Path, repo_url: RepoUrlParts) -> None:
    cfg = RepoTestData()

    step = StepGetRepositoryGitHub(
        name=cfg.repo_name,
        description=cfg.repo_name + " description",
        target_directory=cfg.destination_folder,
        repo_url_parts=repo_url,
        repo_ref=cfg.main_branch,
    ).add_extra(StepGetRepositoryExtraDepthOne(on_local_checkout=True, on_github_action_checkout=True))

    orchestrator = create_orchestrator_factory_all_supported_cases("myName", "0.0.0", "exec-job")
    orchestrator.add_phase(Phase(name="repos checkout").add_step(step))

    orchestrator_validated_opt = create_validated_orchestrator(orchestrator)

    assert orchestrator_validated_opt.orchestrator is not None
    orchestrator = orchestrator_validated_opt.orchestrator
    assert orchestrator is not None

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

    ovb = OrchestratorVisitorLocalExecutor(context=context)

    # execute the orchestrator visitor, which will execute the step to clone the repo
    report = execute_orchestrator(orchestrator, ovb, OrchestratorExecutorReporterDummy())
    assert not executor_visit_reports_has_any_error(report)

    # execute the orchestrator visitor a second time, which will execute the step to update the repo,
    # which should succeed without errors
    report = execute_orchestrator(orchestrator, ovb, OrchestratorExecutorReporterDummy())
    assert not executor_visit_reports_has_any_error(report)
