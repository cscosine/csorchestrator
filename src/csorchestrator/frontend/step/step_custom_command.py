import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import TextIO

from csorchestrator.domain.context.context_compiler_generator import GeneratorType
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import (
    StepBase,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    MatrixOsArchCompilerGeneratorGithubConstants,
    create_context_os_architecture_compiler_generator_string_github_matrix,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import StepRunCommand
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.local_execution.context_local_execution import (
    ContextLocalExecution,
)
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import StepCapabilityLocalExecution
from csorchestrator.frontend.local_execution.step_utils import StepExecuteOnlyOn, StepGithubIfAlways


@dataclass
class StepBashScriptCommandCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepBashScriptCommand"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_custom_command_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepBashScriptCommandCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepBashScriptCommand"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_custom_command(self.step, context, reporter_sink)


@dataclass(kw_only=True)
class StepBashScriptCommand(StepBase):
    cmd: list[str] = field(default_factory=list)
    dry_run: bool = False

    def __post_init__(self) -> None:
        self.add_capability(StepBashScriptCommandCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepBashScriptCommandCapabilityLocalExecution(self), StepCapabilityLocalExecution)


@dataclass
class StepWinPSCommandCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepWinPSCommand"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_win_ps_command_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepWinPSCommandCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepWinPSCommand"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_win_ps_command(self.step, context, reporter_sink)


@dataclass(kw_only=True)
class StepWinPSCommand(StepBase):
    cmd: list[str] = field(default_factory=list)
    dry_run: bool = False

    def __post_init__(self) -> None:
        self.add_capability(StepWinPSCommandCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepWinPSCommandCapabilityLocalExecution(self), StepCapabilityLocalExecution)


@dataclass(kw_only=True)
class StepInstallAptPackages(StepBashScriptCommand):
    packages: list[str]

    def __post_init__(self) -> None:
        super().__post_init__()  # call parent

        script = [
            "set -euo pipefail # enable strict mode",
            "",
            "",
            "packages=(",
        ]
        script += [f"  {p}" for p in self.packages]
        script += [
            ")",
            "",
            "missing=()",
            "",
            'for pkg in "${packages[@]}"; do',
            '  dpkg -s "$pkg" &>/dev/null || missing+=("$pkg")',
            "done",
            "",
            "if [ ${#missing[@]} -ne 0 ]; then",
            "",
            "  sudo apt update",
            "",
            '  echo "Need to install missing packages: ${missing[*]}"',
            '  sudo apt install -y "${missing[@]}"',
            "else",
            '  echo "All packages already installed."',
            "fi",
        ]

        self.cmd = script


def execute_command(
    cmd: list[str], working_dir_full_path: Path, reporter_sink: ReporterSinkBase
) -> list[str]:  # return errors, if any

    errors: list[str] = []

    process = subprocess.Popen(
        cmd,
        cwd=str(working_dir_full_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def stream(
        pipe: TextIO,
        sink_func: Callable[[str], None],
    ) -> None:
        try:
            for line in iter(pipe.readline, ""):
                if line:
                    sink_func(line.rstrip("\n"))
        finally:
            pipe.close()

    stdout_thread = threading.Thread(
        target=stream,
        args=(process.stdout, reporter_sink.stdout),
        daemon=True,
    )

    stderr_thread = threading.Thread(
        target=stream,
        args=(process.stderr, reporter_sink.stderr),
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()

    return_code = None
    try:
        return_code = process.wait()
    except Exception as e:
        process.kill()
        errors += [f"Failed to run cmake workflow: {e}"]
        # do not return, attempt to close threads

    stdout_thread.join()
    stderr_thread.join()

    if return_code is not None and return_code != 0:
        errors += [f"Command failed with exit code {return_code}"]
        # do not return immediately, do at cycle end

    return errors


def evaluate_cmd_variable_subst_local(cmd: list[str], context: ContextLocalExecution) -> list[str]:
    c_cpp_compiler = context.active_compiler_generator.compiler_family.get_c_cpp_compiler()
    toolset = context.active_compiler_generator.compiler_family.get_cmake_toolset()

    subst: dict[str, str] = {
        "CS_DIR_FROM_MATRIX": create_context_os_architecture_compiler_generator_string(
            context.get_active_os_architecture_compiler_generator()
        ),
        # variables
        "CS_MATRIX_EXEC_ID": str(context.matrix_execution_id),
        "CS_OS": context.os_architecture.os.value.lower(),
        "CS_OS_VERSION": context.os_architecture.os_version.lower(),
        "CS_ARCHITECTURE": context.os_architecture.architecture.value.lower(),
        "CS_ARCHITECTURE_VARIANT": context.os_architecture.architecture_variant.lower(),
        "CS_COMPILER_FAMILY": context.active_compiler_generator.compiler_family.value.lower(),
        "CS_COMPILER_VERSION": context.active_compiler_generator.compiler_version.lower(),
        "CS_GENERATOR": context.active_compiler_generator.build_generator.generator.value.lower(),
        "CS_GENERATOR_TYPE": context.active_compiler_generator.build_generator.generator_type.value.lower(),
        "CS_GENERATOR_TYPE_SINGLECONFIG": GeneratorType.SINGLE_CONFIG.value,
        "CS_GENERATOR_TYPE_MULTICONFIG": GeneratorType.MULTI_CONFIG.value,
        "CS_GENERATOR_CMAKE": context.active_compiler_generator.build_generator.generator.get_cmake_generator_name()
        or "",
        "CS_C_COMPILER": c_cpp_compiler[0] or "",
        "CS_CPP_COMPILER": c_cpp_compiler[1] or "",
        "CS_TOOLSET": toolset or "",
    }
    subst_cmd = [Template(c).safe_substitute(subst) for c in cmd]
    return subst_cmd


def evaluate_cmd_variable_subst_github_wf(cmd: list[str]) -> list[str]:
    subst: dict[str, str] = {
        "CS_DIR_FROM_MATRIX": create_context_os_architecture_compiler_generator_string_github_matrix(),
        "CS_MATRIX_EXEC_ID": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_EXECUTION_ID_EMBRACED,
        "CS_OS": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_NAME_EMBRACED,
        "CS_OS_VERSION": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_VERSION_EMBRACED,
        "CS_ARCHITECTURE": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_EMBRACED,
        "CS_ARCHITECTURE_VARIANT": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_VARIANT_EMBRACED,
        "CS_COMPILER_FAMILY": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_EMBRACED,
        "CS_COMPILER_VERSION": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_VERSION_EMBRACED,
        "CS_GENERATOR": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_EMBRACED,
        "CS_GENERATOR_TYPE": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_TYPE_EMBRACED,
        "CS_GENERATOR_TYPE_SINGLECONFIG": GeneratorType.SINGLE_CONFIG.value,
        "CS_GENERATOR_TYPE_MULTICONFIG": GeneratorType.MULTI_CONFIG.value,
        "CS_GENERATOR_CMAKE": MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_CMAKE_EMBRACED,
        "CS_C_COMPILER": MatrixOsArchCompilerGeneratorGithubConstants.C_COMPILER_EMBRACED,
        "CS_CPP_COMPILER": MatrixOsArchCompilerGeneratorGithubConstants.CPP_COMPILER_EMBRACED,
        "CS_TOOLSET": MatrixOsArchCompilerGeneratorGithubConstants.TOOLSET_EMBRACED,
    }
    subst_cmd = []
    for c in cmd:
        print(c)
        cc = Template(c).safe_substitute(subst)
        print(cc)

        subst_cmd += [cc]

    return subst_cmd


def execute_step_custom_command(
    step: StepBashScriptCommand, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    cmd_evaluated = evaluate_cmd_variable_subst_local(step.cmd, context)
    cmd_string = ["bash", "-c", "\n".join(cmd_evaluated)]

    reporter_sink.stdout("\n".join(cmd_string))
    if not step.dry_run:
        errors = execute_command(cmd_string, context.base_folder_path, reporter_sink)
        for e in errors:
            report.append_error(e)

    return report


def get_if_str(step: StepBase) -> str | None:
    if step.get_extra(StepExecuteOnlyOn) is not None:
        execute_only_on_extra = step.get_extra(StepExecuteOnlyOn)
        if execute_only_on_extra is not None:
            os_str = execute_only_on_extra.os.value.lower()
            if_str = "${{" + f" {MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_NAME} == '{os_str}'"
            if execute_only_on_extra.version_starts_with is not None:
                if_str = (
                    if_str + f" && startsWith({MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_VERSION}, "
                    f"'{execute_only_on_extra.version_starts_with}')"
                )
            if execute_only_on_extra.arch is not None:
                if_str = (
                    if_str + f" && {MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE} == "
                    f"'{execute_only_on_extra.arch.value.lower()}'"
                )
            if_str = if_str + " }}"

            return if_str
    elif step.get_extra(StepGithubIfAlways) is not None:
        execute_alwayw = step.get_extra(StepGithubIfAlways)
        if execute_alwayw is not None:
            if_str = "always()"
            return if_str
    return None


def step_custom_command_to_githubwf(
    step: StepBashScriptCommand, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    cmd_evaluated = evaluate_cmd_variable_subst_github_wf(step.cmd)

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name=f"Run command {step.name}",
            if_str=get_if_str(step),
            shell_type="bash",
            run=cmd_evaluated,
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())


# ------------------------------


def execute_step_win_ps_command(
    step: StepWinPSCommand, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    cmd_evaluated = evaluate_cmd_variable_subst_local(step.cmd, context)
    cmd_string = ["powershell", "-Command", "; ".join(cmd_evaluated)]

    reporter_sink.stdout("\n".join(cmd_string))
    if not step.dry_run:
        errors = execute_command(cmd_string, context.base_folder_path, reporter_sink)
        for e in errors:
            report.append_error(e)

    return report


def step_win_ps_command_to_githubwf(
    step: StepWinPSCommand, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    cmd_evaluated = evaluate_cmd_variable_subst_github_wf(step.cmd)

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name=f"Run command {step.name}",
            if_str=get_if_str(step),
            shell_type="powershell",
            run=cmd_evaluated,
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
