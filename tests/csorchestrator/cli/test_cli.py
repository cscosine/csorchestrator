import textwrap
from pathlib import Path

import pytest

from csorchestrator.application.cli.cli import main as csorchestrator_main
from csorchestrator.domain.execution.execution import ExecutionResult


def test_run_command_loads_project_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "project.py"
    script_path.write_text(
        textwrap.dedent(
            """
            from typing import TypeAlias
            from pathlib import Path
            from csorchestrator.foundation.core.report import Report
            from csorchestrator.application.factory.factory import OptionalOrchestratorWithReport
            from csorchestrator.domain.orchestrator.orchestrator import Orchestrator

            def create_orchestrator() -> OptionalOrchestratorWithReport:
                return OptionalOrchestratorWithReport.create_result_and_report(
                    Orchestrator("myName", "0.0.0", "exec-job"), Report()
                )
            """
        )
    )

    executed = {"called": False}

    def fake_validate_and_execute_orchestrator(orchestrator, script_folder_path, target_folder_path, reporter):
        assert Path(target_folder_path) == script_path.parent
        executed["called"] = True
        return ExecutionResult()

    from csorchestrator.application.cli import cli as mod

    monkeypatch.setattr(mod, "validate_and_execute_orchestrator", fake_validate_and_execute_orchestrator)

    result = csorchestrator_main(["run", str(script_path)])

    assert result == 0
    assert executed["called"]


def test_run_command_missing_create_orchestrator(tmp_path: Path) -> None:
    script_path = tmp_path / "project.py"
    script_path.write_text("a = 1\n")

    result = csorchestrator_main(["run", str(script_path)])
    assert result == 1
