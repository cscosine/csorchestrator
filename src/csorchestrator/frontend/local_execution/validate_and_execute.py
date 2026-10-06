from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from csorchestrator.domain.context.context_os_architecture import ContextOsArchitecture, detect_context_os_architecture
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ExecutionMatrixOsArchCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.execution.execution import ExecutionResult
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.orchestrator_executor import (
    execute_orchestrator,
    executor_visit_reports_has_any_error,
)
from csorchestrator.domain.orchestrator.orchestrator_executor_reporter_base import OrchestratorExecutorReporterBase
from csorchestrator.foundation.core.optional_result_with_report import OptionalResultWithReport
from csorchestrator.foundation.core.report import Report
from csorchestrator.foundation.file_system.directory import ensure_directory_exists_or_create_and_is_usable
from csorchestrator.frontend.local_execution.context_local_execution import (
    ContextLocalExecution,
    ContextLocalExecutionExtra,
)
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import (
    OrchestratorVisitorLocalExecutor,
    ReleaseCreationOnTagConfigBaseCapabilityLocalExecution,
)
from csorchestrator.frontend.local_execution.release_creation_context_local_execution import (
    ReleaseCreationContextLocalExecution,
)
from csorchestrator.frontend.validation.validated_orchestrator import create_validated_orchestrator


@dataclass
class OsArchitectureAndPath:
    os_architecture: ContextOsArchitecture
    path: Path


OptionalOsArchitectureAndPathWithReport: TypeAlias = OptionalResultWithReport[OsArchitectureAndPath]


def create_context_os_architecture_string(
    os_architecture: ContextOsArchitecture,
) -> str:
    parts: list[str] = []
    parts.append(os_architecture.os.value.lower())
    parts.append(os_architecture.os_version.lower())
    parts.append(os_architecture.architecture.value.lower())
    parts.append(os_architecture.architecture_variant.lower())
    return "-".join(parts)


def create_os_and_path(base_folder_path: Path) -> OptionalOsArchitectureAndPathWithReport:
    report = Report()

    pr = ensure_directory_exists_or_create_and_is_usable(base_folder_path)

    if pr.error is not None:
        report.append_error(pr.error)

    osa_expected = detect_context_os_architecture()

    if osa_expected.error is not None:
        report.append_error(osa_expected.error)

    if pr.value is not None and osa_expected.value is not None:
        return OptionalOsArchitectureAndPathWithReport.create_result_and_report(
            OsArchitectureAndPath(os_architecture=osa_expected.value, path=pr.value),
            report,
        )
    else:
        return OptionalOsArchitectureAndPathWithReport.create_report(report)


def validate_and_execute_orchestrator(
    orchestrator: Orchestrator,
    script_folder_path: Path,
    target_folder_path: Path,
    reporter: OrchestratorExecutorReporterBase,
) -> ExecutionResult:
    er = ExecutionResult()
    er.execution_description = orchestrator.extract_minimal_description()
    reporter.report_execution_description(er.execution_description)

    orchestrator_validated_opt = create_validated_orchestrator(orchestrator)
    er.report_pre_execution.append_report(orchestrator_validated_opt.main_report)
    er.report_validation = orchestrator_validated_opt.validation_reports
    reporter.report_validation_report(er.report_validation)

    if orchestrator_validated_opt.orchestrator is None:
        reporter.report_pre_execution_report(er.report_pre_execution)
        reporter.finalize_execution()
        return er

    orchestrator = orchestrator_validated_opt.orchestrator

    # validated orchestrator, create context

    os_and_path_opt = create_os_and_path(base_folder_path=target_folder_path)
    er.report_pre_execution.append_report(os_and_path_opt.report)

    if os_and_path_opt.result is None:
        reporter.report_pre_execution_report(er.report_pre_execution)
        reporter.finalize_execution()
        return er

    # finalized the pre execution
    reporter.report_pre_execution_report(er.report_pre_execution)

    os_and_path = os_and_path_opt.result

    matrix = orchestrator.execution_matrix

    matrix_extras: dict[type, ContextLocalExecutionExtra] = {}

    assert isinstance(matrix, ExecutionMatrixOsArchCompilerGenerator)  # ensured by the validator

    # matrix execution

    any_failed = False
    for counter, os_architecture_compiler_generator in enumerate(matrix.os_architecture_compiler_generator_list):
        match = os_architecture_compiler_generator.context_os_architecture.can_be_executed_on(
            os_and_path.os_architecture
        )
        if not match:
            reporter.report_skip_execution(
                "skip orchestrator execution on not compatible matrix config: "
                f"{create_context_os_architecture_compiler_generator_string(os_architecture_compiler_generator)}"
                f", current os and architecture:  {create_context_os_architecture_string(os_and_path.os_architecture)}"
            )
            er.report_executions.append(None)
            continue
        # use the compatible os_architecture, not the detected one.
        # e.g. detected os is win 11, but we select win 10 in the matrix, which is compatible

        context = ContextLocalExecution(
            orchestrator_description=orchestrator.create_orchestrator_description(),
            script_folder_path=script_folder_path,
            base_folder_path=os_and_path.path,
            os_architecture=os_architecture_compiler_generator.context_os_architecture,
            active_compiler_generator=os_architecture_compiler_generator.context_compiler_generator,
            matrix_extras=matrix_extras,
            matrix_execution_id=str(counter),
        )

        # execute
        reporter.report_start_execution(
            "orchestrator execution on matrix config: "
            f"{create_context_os_architecture_compiler_generator_string(os_architecture_compiler_generator)}"
        )

        # execute the orchestrator visitor, which will execute the step to clone the repo, build, etc...
        report_execution = execute_orchestrator(
            orchestrator, OrchestratorVisitorLocalExecutor(context=context), reporter=reporter
        )

        if executor_visit_reports_has_any_error(report_execution):
            reporter.report_execution_report(report_execution)
            er.report_executions.append(report_execution)
            any_failed = True
            break

        reporter.report_execution_report(report_execution)

        er.report_executions.append(report_execution)

        # keep the matrix_extras modified for the next context
        matrix_extras = context.matrix_extras

    # end matrix execution, execute the release part if any
    if any_failed:
        report = Report().append_error("post execution skipped because execution was not successfull")
        reporter.report_postexecution(report)
        er.report_post_execution.append(report)
    else:
        if orchestrator.wf_config is not None and orchestrator.wf_config.create_release_on_tag is not None:
            capability = orchestrator.wf_config.create_release_on_tag.get_capability(
                ReleaseCreationOnTagConfigBaseCapabilityLocalExecution
            )
            if capability is None:
                report = Report().append_error("post execution skipped because capability is not supported")
                reporter.report_postexecution(report)
                er.report_post_execution.append(report)
            else:
                release_context = ReleaseCreationContextLocalExecution(
                    os_architecture_compiler_generator_list=matrix.os_architecture_compiler_generator_list,
                    orchestrator_description=orchestrator.create_orchestrator_description(),
                    os_architecture=os_and_path.os_architecture,
                    script_folder_path=script_folder_path,
                    base_path=os_and_path.path,
                )
                report = capability.execute_locally(release_context)
                reporter.report_postexecution(report)
                er.report_post_execution.append(report)
        else:
            report = Report().append_error("post execution skipped because not configured")
            reporter.report_postexecution(report)

    reporter.finalize_execution()

    return er
