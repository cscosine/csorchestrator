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


def test_describe_command_prints_description(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script_path = tmp_path / "project.py"
    script_path.write_text(
        textwrap.dedent(
            """
            from dataclasses import dataclass

            from csorchestrator.application.factory.factory import OptionalOrchestratorWithReport
            from csorchestrator.domain.orchestrator.orchestrator import MatrixExecutionBase, Orchestrator
            from csorchestrator.domain.orchestrator.step_base import StepBase
            from csorchestrator.foundation.core.report import Report


            @dataclass
            class SimpleStep(StepBase):
                pass


            @dataclass
            class SimpleMatrix(MatrixExecutionBase):
                def to_list_string_description(self) -> list[str]:
                    return ["matrix entry one"]


            def create_orchestrator() -> OptionalOrchestratorWithReport:
                o = Orchestrator("myName", "0.0.0", SimpleMatrix("exec-job"))
                o.create_phase("build").add_step(SimpleStep(name="compile", description="compile")).add_step(
                    SimpleStep(name="link", description="link")
                )
                o.create_phase("test").add_step(SimpleStep(name="unit", description="unit tests"))
                return OptionalOrchestratorWithReport.create_result_and_report(o, Report())
            """
        )
    )

    from csorchestrator.application.cli import cli as mod

    def fail_if_executed(*args: object, **kwargs: object) -> None:
        raise AssertionError("describe must not execute the orchestrator")

    monkeypatch.setattr(mod, "validate_and_execute_orchestrator", fail_if_executed)

    markdown_path = tmp_path / "description.md"
    result = csorchestrator_main(["--sink", "print", "--markdown", str(markdown_path), "describe", str(script_path)])

    assert result == 0

    captured = capsys.readouterr().out
    assert "[cout] Orchestrator: myName-0.0.0" in captured
    assert "[cout] Phase: build" in captured
    assert "[cout]   Step: compile" in captured
    assert "[cout]   Step: link" in captured
    assert "[cout] Phase: test" in captured
    assert "[cout]   Step: unit" in captured
    assert "[cout] Matrix Description" in captured
    assert "[cout]   matrix entry one" in captured

    markdown_content = markdown_path.read_text(encoding="utf-8")
    assert "## Execution Description" in markdown_content
    assert "### Phase: build" in markdown_content
    assert "- Step: compile" in markdown_content


def test_describe_command_missing_create_orchestrator(tmp_path: Path) -> None:
    script_path = tmp_path / "project.py"
    script_path.write_text("a = 1\n")

    result = csorchestrator_main(["--sink", "print", "describe", str(script_path)])
    assert result == 1
