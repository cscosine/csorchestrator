#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Literal, cast

import click

from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.orchestrator_executor_reporter_base import OrchestratorExecutorReporterBase
from csorchestrator.foundation.core.expected import Expected
from csorchestrator.foundation.core.optional_result_with_report import OptionalResultWithReport
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.validate_and_generate_github_workflow import (
    validate_and_generate_github_workflow,
)
from csorchestrator.frontend.local_execution.validate_and_execute import validate_and_execute_orchestrator
from csorchestrator.frontend.reporters.orchestrator_executor_reporter_composite import (
    OrchestratorExecutorReporterComposite,
)
from csorchestrator.frontend.reporters.orchestrator_executor_reporter_markdown import (
    OrchestratorExecutorReporterMarkdown,
)
from csorchestrator.frontend.reporters.orchestrator_executor_reporter_print import OrchestratorExecutorReporterPrint
from csorchestrator.frontend.reporters.reporter_sink_colorama_print import ReporterSinkColoramaPrint
from csorchestrator.frontend.reporters.reporter_sink_colored_print import ReporterSinkColoredPrint
from csorchestrator.frontend.reporters.reporter_sink_print import ReporterSinkPrint, ReporterSinkPrintBase

CreateOrchestratorFn = Callable[[], OptionalResultWithReport[Orchestrator]]

SINK_TYPES = ("print", "colored", "colorama", "none")
SinkType = Literal["print", "colored", "colorama", "none"]  # keep aligned with SINK_TYPES


def _build_sink(kind: str) -> ReporterSinkPrintBase | None:
    if kind == "print":
        return ReporterSinkPrint()
    elif kind == "colored":
        return ReporterSinkColoredPrint()
    elif kind == "colorama":
        return ReporterSinkColoramaPrint()
    elif kind == "none":
        return None
    else:
        r = ReporterSinkPrint()
        r.stderr(f"Unknown sink type: {kind}, fallback to ReporterSinkPrint")
        return r


@dataclass
class CLIConfig:
    sink: SinkType = "colorama"
    markdown_path: Path | None = None


@click.group(help="csorchestrator command line interface")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--sink",
    type=click.Choice(SINK_TYPES),
    default="colorama",
    show_default=True,
    help="Select reporter sink implementation",
)
@click.option(  # type: ignore[untyped-decorator]
    "--markdown",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write execution report as markdown file",
)
@click.pass_context  # type: ignore[untyped-decorator]
def app(ctx: click.Context, sink: str, markdown: Path | None = None) -> None:
    config = CLIConfig(sink=cast(SinkType, sink), markdown_path=markdown)
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


def load_project_module(script_path: Path) -> Expected[ModuleType, str]:
    """Load a Python module from a file path."""
    script_path = script_path.resolve()
    module_name = f"csorchestrator_project_{script_path.stem}_{abs(hash(script_path))}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        return Expected[ModuleType, str].make_error(f"Unable to load project file '{script_path}'")

    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return Expected[ModuleType, str].make_value(module)


def resolve_target_folder(script_path: Path, target_folder: Path | None) -> Path:
    """Resolve the target folder, defaulting to script parent directory."""
    if target_folder is None:
        return script_path.parent.resolve()
    return target_folder.resolve()


def assert_create_orchestrator(module: ModuleType) -> Expected[CreateOrchestratorFn, str]:
    """Assert that the module defines create_orchestrator and return it."""
    if not hasattr(module, "create_orchestrator"):
        return Expected[CreateOrchestratorFn, str].make_error("Project script does not define create_orchestrator()")
    return Expected[CreateOrchestratorFn, str].make_value(module.create_orchestrator)


def project_script_preparation(script_path: Path, reporter: OrchestratorExecutorReporterBase) -> Orchestrator | None:

    module_or_error = load_project_module(script_path)
    if module_or_error.error is not None:
        report = Report()
        report.append_error(module_or_error.error)
        reporter.report_orchestrator_creation_report(report)
        return None

    assert module_or_error.value is not None
    module = module_or_error.value

    create_orchestrator_expected = assert_create_orchestrator(module)
    if create_orchestrator_expected.error is not None:
        report = Report()
        report.append_error(create_orchestrator_expected.error)
        reporter.report_orchestrator_creation_report(report)
        return None

    assert create_orchestrator_expected.value is not None
    create_orchestrator = create_orchestrator_expected.value

    orchestrator_result = create_orchestrator()

    reporter.report_orchestrator_creation_report(orchestrator_result.report)

    return orchestrator_result.result


def execute_project_script(
    script_path: Path, target_folder: Path | None, reporter: OrchestratorExecutorReporterBase
) -> int:
    """Load and execute a project script's create_orchestrator() function."""

    target_folder = resolve_target_folder(script_path, target_folder)

    orchestrator_or_none = project_script_preparation(script_path, reporter)
    if orchestrator_or_none is None:
        return 1
    orchestrator = orchestrator_or_none

    res = validate_and_execute_orchestrator(
        orchestrator=orchestrator,
        script_folder_path=script_path.parent.resolve(),
        target_folder_path=target_folder,
        reporter=reporter,
    )

    if res.is_execution_successful():
        return 0
    return 1


def generate_github_workflow_project_script(
    script_path: Path, output_path: Path | None, reporter: OrchestratorExecutorReporterBase
) -> int:
    """Load a project script's create_orchestrator() function and use it to generate a github wf."""

    orchestrator_or_none = project_script_preparation(script_path, reporter)
    if orchestrator_or_none is None:
        return 1

    res = validate_and_generate_github_workflow(
        orchestrator_or_none, script_path.parent.resolve(), output_path, reporter
    )
    if res.is_execution_successful():
        return 0

    return 1


def _build_reporter(config: CLIConfig) -> tuple[OrchestratorExecutorReporterComposite, ReporterSinkPrintBase | None]:
    """Build the composite reporter for a CLI command; also returns the console sink for direct use."""
    reporter = OrchestratorExecutorReporterComposite()
    console_sink = _build_sink(config.sink)
    if console_sink is not None:
        reporter.reporters.append(OrchestratorExecutorReporterPrint(reporter_sink=console_sink))
    if config.markdown_path is not None:
        reporter.reporters.append(OrchestratorExecutorReporterMarkdown(path=config.markdown_path))
    return reporter, console_sink


def describe_project_script(
    script_path: Path, console_sink: ReporterSinkPrintBase | None, reporter: OrchestratorExecutorReporterBase
) -> int:
    """Load a project script's create_orchestrator() function and report only its description."""

    orchestrator_or_none = project_script_preparation(script_path, reporter)
    if orchestrator_or_none is None:
        return 1

    orchestrator = orchestrator_or_none

    if console_sink is not None:
        console_sink.stdout(f"Orchestrator: {orchestrator.name_version_to_string()}")

    reporter.report_execution_description(orchestrator.extract_minimal_description())
    reporter.finalize_execution()

    return 0


@app.command("run")  # type: ignore[untyped-decorator]
@click.argument(
    "script_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)  # type: ignore[untyped-decorator]
@click.option(
    "--target-folder",
    "-t",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Base folder for orchestrator execution. Defaults to the project script location.",
)  # type: ignore[untyped-decorator]
@click.pass_context  # type: ignore[untyped-decorator]
def run(ctx: click.Context, script_path: Path, target_folder: Path | None) -> int:
    """Load a Python project script and execute its create_orchestrator() result."""
    config: CLIConfig = ctx.obj["config"]

    reporter, _ = _build_reporter(config)

    return execute_project_script(script_path, target_folder, reporter)


@app.command("generate-github-workflow")  # type: ignore[untyped-decorator]
@click.argument(
    "script_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)  # type: ignore[untyped-decorator]
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write workflow to this file. Defaults to stdout.",
)  # type: ignore[untyped-decorator]
@click.pass_context  # type: ignore[untyped-decorator]
def gen_wf(ctx: click.Context, script_path: Path, output: Path | None) -> int:
    """Load a Python project script and create the gitHub workflow for create_orchestrator() result."""
    config: CLIConfig = ctx.obj["config"]

    reporter, _ = _build_reporter(config)

    return generate_github_workflow_project_script(script_path, output, reporter)


@app.command("describe")  # type: ignore[untyped-decorator]
@click.argument(
    "script_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)  # type: ignore[untyped-decorator]
@click.pass_context  # type: ignore[untyped-decorator]
def describe(ctx: click.Context, script_path: Path) -> int:
    """Load a Python project script and emit only its orchestrator description (no execution)."""
    config: CLIConfig = ctx.obj["config"]

    reporter, console_sink = _build_reporter(config)

    return describe_project_script(script_path, console_sink, reporter)


COMMANDS_WITH_OPTIONAL_SCRIPT = {
    "run",
    "describe",
    "generate-github-workflow",
}


def _same_script(a: str, b: str) -> bool:
    return Path(a).resolve() == Path(b).resolve()


def orchestrator_main_with_default_run(
    script_path: str,
    argv: Sequence[str] | None,
) -> int:
    if argv is None:
        argv = sys.argv[1:]

    argv = list(argv)

    # early exit for help
    if argv in (["--help"], ["-h"]):
        return main(argv)

    # No args:
    # ./project.py
    # -> run project.py
    if not argv:
        argv = ["run", script_path]

    else:
        command = argv[0]

        # No explicit command:
        # ./project.py foo bar
        # -> run project.py foo bar
        if command not in COMMANDS_WITH_OPTIONAL_SCRIPT:
            argv = ["run", script_path, *argv]

        else:
            # Handle commands with optional script parameter
            if len(argv) == 1:
                # ./project.py run
                # ./project.py generate-github-workflow
                argv.append(script_path)

            else:
                supplied_script = argv[1]

                if not _same_script(supplied_script, script_path):
                    raise SystemExit(f"This wrapper only operates on {script_path}, not {supplied_script}")

    return main(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    try:
        result = app.main(args=argv, standalone_mode=False)

    except click.ClickException as exc:
        exc.show()
        return cast(int, exc.exit_code)

    except click.Abort:
        click.echo("Aborted!", err=True)
        return 1

    except SystemExit as exc:
        return int(exc.code or 0)

    if result is None:
        return 0

    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
