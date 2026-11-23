from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from csorchestrator.domain.context.context_compiler_generator import GeneratorType
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import (
    StepBase,
    StepExtra,
)
from csorchestrator.foundation.core.expected import Expected
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.cscmake_presets.supported_variants import (
    BuildConfig,
    ContextOsArchitectureCompilerGeneratorConfig,
    get_all_supported_workflow_descriptions,
    get_supported_build_configs_for_generator_type,
    is_config_selected_for_generator,
    workflow_name_from_description,
    workflow_name_from_matrix_components,
)
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    MatrixOsArchCompilerGeneratorGithubConstants,
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
from csorchestrator.frontend.step.step_custom_command import execute_command, get_if_str


@dataclass
class StepCMakeWorkflowCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepCMakeWorkflow"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        if self.step.get_extra(StepCMakeWorkflowGithubPowershell):
            return step_cmake_workflow_to_githubwf_powershell(self.step, wf_job, reporter_sink)
        return step_cmake_workflow_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepCMakeWorkflowCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepCMakeWorkflow"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_cmake_workflow(self.step, context, reporter_sink)


@dataclass
class StepCMakeWorkflow(StepBase):
    source_dir: str
    config: BuildConfig

    def __post_init__(self) -> None:
        self.add_capability(StepCMakeWorkflowCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepCMakeWorkflowCapabilityLocalExecution(self), StepCapabilityLocalExecution)


@dataclass
class StepCMakeWorkflowGithubPowershell(StepExtra):
    pass


@dataclass
class StepCMakeWorkflowGithubExtraCommandsPrefix(StepExtra):
    cmd: list[str]

    @classmethod
    def get_extra_cmd_prefix(cls, repo_step: StepCMakeWorkflow) -> list[str]:
        extra_cmd_prefix = []
        extra_cmd_prefix_opt = repo_step.get_extra(StepCMakeWorkflowGithubExtraCommandsPrefix)
        if extra_cmd_prefix_opt is not None:
            extra_cmd_prefix = extra_cmd_prefix_opt.cmd
        return extra_cmd_prefix


ContextWorkflowsExpected: TypeAlias = Expected[
    tuple[
        ContextOsArchitectureCompilerGenerator,
        list[ContextOsArchitectureCompilerGeneratorConfig],
    ],
    str,
]


def get_context_and_workflows(
    config: BuildConfig,
    context_os_architecture_compiler_generator: ContextOsArchitectureCompilerGenerator,
) -> ContextWorkflowsExpected:

    workflow_configs = get_all_supported_workflow_descriptions(
        selected_config=config,
        os_arch_generator=context_os_architecture_compiler_generator,
    )

    if len(workflow_configs) == 0:
        return ContextWorkflowsExpected.make_error("no workflows are supported in the current execution context")

    return ContextWorkflowsExpected.make_value((context_os_architecture_compiler_generator, workflow_configs))


def execute_step_cmake_workflow(
    step: StepCMakeWorkflow, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    # retrieve the current execution context or infer it from the matrix
    res_or_err = get_context_and_workflows(
        config=step.config,
        context_os_architecture_compiler_generator=context.get_active_os_architecture_compiler_generator(),
    )

    if res_or_err.error is not None:
        report.append_error(res_or_err.error)
        return report

    assert res_or_err.value is not None
    context_os_architecture_compiler_generator, workflow_configs = res_or_err.value
    assert context_os_architecture_compiler_generator is not None

    for workflow_config in workflow_configs:
        workflow_name = workflow_name_from_description(workflow_config)

        target_full_path: Path = context.base_folder_path / step.source_dir
        cmd = [
            "cmake",
            "--workflow",
            "--preset",
            workflow_name,
        ]
        report.append_info(f"Run cmake workflow with command: {' '.join(cmd)} in {target_full_path}")
        errors = execute_command(cmd, target_full_path, reporter_sink)
        for e in errors:
            report.append_error(e)

        if report.has_errors():
            return report  # early exit

    return report


def step_cmake_workflow_to_githubwf_powershell(
    step: StepCMakeWorkflow, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:
    # create a step with a if inside base on single/multi config (
    # - in single config need to launch N cmake workflow if I have to configure/build/test N
    # - in multi config the command is one
    run_str_list = []
    run_str_list += StepCMakeWorkflowGithubExtraCommandsPrefix.get_extra_cmd_prefix(step)
    run_str_list += [f'$gen = "{MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_TYPE_EMBRACED}"']
    first_cycle = False
    for generator_type in GeneratorType:
        if_elif_str = "if" if not first_cycle else "elseif"
        run_str_list += [if_elif_str + " ($gen -eq " + '"' + generator_type.value + '") {']
        first_cycle = True
        generator_supported_configs = get_supported_build_configs_for_generator_type(generator_type)
        selected_configs = []
        for supported_config in generator_supported_configs:
            if is_config_selected_for_generator(
                generator_type, current_config=supported_config, requested_config=step.config
            ):
                selected_configs += [supported_config]

        if len(selected_configs) == 0:
            return OptionalListGithubStepsWithReport.create_report(
                Report().append_error(
                    f"Requested config {step.config.value} is not supported for generator type {generator_type.value}"
                )
            )

        for config in selected_configs:
            wf_name = workflow_name_from_matrix_components(config.value)
            run_str_list += ["  cmake --workflow " + wf_name]
        run_str_list += ["}"]
    if not first_cycle:
        return OptionalListGithubStepsWithReport.create_report(
            Report().append_error("Defensive: no generators in for loop in step_cmake_workflow_to_githubwf?!?")
        )

    run_str_list += ["else {"]
    run_str_list += ['   Write-Host "Unknown generator_type: $gen"']
    run_str_list += ["  exit 1"]
    run_str_list += ["}"]

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name=f"cmake workflow on {step.name} for config(s) {step.config.value}",
            shell_type="powershell",
            run=run_str_list,
            if_str=get_if_str(step),
            working_directory=step.source_dir,
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())


def step_cmake_workflow_to_githubwf(
    step: StepCMakeWorkflow, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    # create a step with a if inside base on single/multi config (
    # - in single config need to launch N cmake workflow if I have to configure/build/test N
    # - in multi config the command is one
    run_str_list = ["set -e"]
    run_str_list += StepCMakeWorkflowGithubExtraCommandsPrefix.get_extra_cmd_prefix(step)
    first_cycle = False
    for generator_type in GeneratorType:
        generator_type_matrix_embraced = MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_TYPE_EMBRACED
        if_elif_str = "if" if not first_cycle else "elif"
        run_str_list += [
            if_elif_str + ' [[ "' + generator_type_matrix_embraced + '" == ' + '"' + generator_type.value + '" ]]; then'
        ]
        first_cycle = True
        generator_supported_configs = get_supported_build_configs_for_generator_type(generator_type)
        selected_configs = []
        for supported_config in generator_supported_configs:
            if is_config_selected_for_generator(
                generator_type, current_config=supported_config, requested_config=step.config
            ):
                selected_configs += [supported_config]

        if len(selected_configs) == 0:
            return OptionalListGithubStepsWithReport.create_report(
                Report().append_error(
                    f"Requested config {step.config.value} is not supported for generator type {generator_type.value}"
                )
            )

        for config in selected_configs:
            wf_name = workflow_name_from_matrix_components(config.value)
            run_str_list += ["  cmake --workflow " + wf_name]
    if not first_cycle:
        return OptionalListGithubStepsWithReport.create_report(
            Report().append_error("Defensive: no generators in for loop in step_cmake_workflow_to_githubwf?!?")
        )

    run_str_list += ["else"]
    run_str_list += [
        '  echo "Unknown generator_type: '
        f'{MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_TYPE_EMBRACED}"'
    ]
    run_str_list += ["  exit 1"]
    run_str_list += ["fi"]

    steps: list[GithubStepInterface] = [
        StepRunCommand(
            name=f"cmake workflow on {step.name} for config(s) {step.config.value}",
            shell_type="bash",
            run=run_str_list,
            if_str=get_if_str(step),
            working_directory=step.source_dir,
        )
    ]

    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
