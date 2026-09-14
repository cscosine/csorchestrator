import shutil
from importlib.resources import as_file, files
from pathlib import Path
from typing import TypeAlias

import yaml

from csorchestrator.domain.context.context_compiler_generator import ContextCompilerGenerator, Generator
from csorchestrator.domain.context.context_os_architecture import (
    OS,
    UBUNTU_STRING_PREFIX,
    Architecture,
    UbuntuVersions,
    WindowsVersions,
)
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    ExecutionMatrixOsArchCompilerGenerator,
)
from csorchestrator.domain.execution.execution import ExecutionResult
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.orchestrator_executor import execute_orchestrator
from csorchestrator.domain.orchestrator.orchestrator_executor_reporter_base import OrchestratorExecutorReporterBase
from csorchestrator.domain.orchestrator.workflow_config import WorkflowTrigger
from csorchestrator.foundation.core.expected import Expected
from csorchestrator.foundation.file_system.directory import ensure_directory_exists_or_create_and_is_usable
from csorchestrator.frontend.github_workflow_translation.github_workflow_config import (
    GitHubWorkflow,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_create_release import (
    JobReleaseCreationFromArtifacts,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_matrix_execution import (
    MatrixOsArchCompilerGeneratorRunnerEntryInclude,
    create_job_from_matrix_list,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OrchestratorVisitorGitHubWorkflowPreparation,
)
from csorchestrator.frontend.github_workflow_translation.release_creation_context import ReleaseCreationContext
from csorchestrator.frontend.validation.validated_orchestrator import create_validated_orchestrator

OrchestratorMatrixToGitHubWFExpected: TypeAlias = Expected[
    list[MatrixOsArchCompilerGeneratorRunnerEntryInclude], list[str]
]  # str is the error messages

GITHUB_RUNNER_UBUNTU_22_04 = UBUNTU_STRING_PREFIX + "-22.04"
GITHUB_RUNNER_UBUNTU_22_04_ARM64 = GITHUB_RUNNER_UBUNTU_22_04 + "-arm"

GITHUB_RUNNER_UBUNTU_24_04 = UBUNTU_STRING_PREFIX + "-24.04"
GITHUB_RUNNER_UBUNTU_24_04_ARM64 = GITHUB_RUNNER_UBUNTU_24_04 + "-arm"

GITHUB_RUNNER_WINDOWS_2022 = OS.WINDOWS.value + "-2022"
GITHUB_RUNNER_WINDOWS_2025_VS2026 = OS.WINDOWS.value + "-2025-vs2026"


def get_runner(entry: ContextOsArchitectureCompilerGenerator) -> Expected[str, str]:
    os = entry.context_os_architecture.os
    os_version = entry.context_os_architecture.os_version
    arch = entry.context_os_architecture.architecture
    generator = entry.context_compiler_generator.build_generator.generator
    compiler_version = entry.context_compiler_generator.compiler_version

    if os == OS.LINUX:
        if os_version == UbuntuVersions.UBUNTU_22_04.value and arch == Architecture.X64:
            return Expected[str, str].make_value(GITHUB_RUNNER_UBUNTU_22_04)
        elif os_version == UbuntuVersions.UBUNTU_24_04.value and arch == Architecture.X64:
            return Expected[str, str].make_value(GITHUB_RUNNER_UBUNTU_24_04)
        elif os_version == UbuntuVersions.UBUNTU_22_04.value and arch == Architecture.ARM64:
            return Expected[str, str].make_value(GITHUB_RUNNER_UBUNTU_22_04_ARM64)
        elif os_version == UbuntuVersions.UBUNTU_24_04.value and arch == Architecture.ARM64:
            return Expected[str, str].make_value(GITHUB_RUNNER_UBUNTU_24_04_ARM64)
    elif os == OS.WINDOWS and os_version == WindowsVersions.WIN10.value and arch == Architecture.X64:
        if generator == Generator.MSVC_17_2022:
            return Expected[str, str].make_value(GITHUB_RUNNER_WINDOWS_2022)
        elif generator == Generator.MSVC_18_2026:
            return Expected[str, str].make_value(GITHUB_RUNNER_WINDOWS_2025_VS2026)
        elif generator == Generator.NINJA or generator == Generator.NINJA_MULTI:
            if compiler_version == ContextCompilerGenerator.COMPILER_VERSION_MSVC_2026_18:
                return Expected[str, str].make_value(GITHUB_RUNNER_WINDOWS_2025_VS2026)
            elif compiler_version == ContextCompilerGenerator.COMPILER_VERSION_MSVC_2022_17:
                return Expected[str, str].make_value(GITHUB_RUNNER_WINDOWS_2022)

    return Expected[str, str].make_error(
        f"unsupported config os: {os.value}, os_version: {os_version}, arch: {arch.value}, generator: {generator.value}"
    )


def orchestrator_matrix_to_github_wf_matrix(
    orchestrator_matrix: ExecutionMatrixOsArchCompilerGenerator,
) -> OrchestratorMatrixToGitHubWFExpected:
    res: list[MatrixOsArchCompilerGeneratorRunnerEntryInclude] = []
    errors: list[str] = []

    counter: int = -1
    for entry in orchestrator_matrix.os_architecture_compiler_generator_list:
        counter += 1

        runner_or_err = get_runner(entry)
        if runner_or_err.error is not None:
            errors.append(runner_or_err.error)
            continue

        assert runner_or_err.value is not None
        runner = runner_or_err.value

        generator_cmake = entry.context_compiler_generator.build_generator.generator.get_cmake_generator_name()
        if generator_cmake is None:
            errors.append(
                f"generator {entry.context_compiler_generator.build_generator.generator.value.lower()} does not have a "
                "CMake defined correspondent generator"
            )
            continue

        c_cpp_compiler = entry.context_compiler_generator.compiler_family.get_c_cpp_compiler()
        toolset = entry.context_compiler_generator.compiler_family.get_cmake_toolset()

        res.append(
            MatrixOsArchCompilerGeneratorRunnerEntryInclude(
                original_os_architecture_compiler_generator_list=entry,
                execution_id=str(counter),
                os=entry.context_os_architecture.os.value.lower(),
                os_version=entry.context_os_architecture.os_version.lower(),
                architecture=entry.context_os_architecture.architecture.value.lower(),
                architecture_variant=entry.context_os_architecture.architecture_variant.lower(),
                compiler=entry.context_compiler_generator.compiler_family.value.lower(),
                compiler_version=entry.context_compiler_generator.compiler_version.lower(),
                build_generator=entry.context_compiler_generator.build_generator.generator.value.lower(),
                build_generator_type=entry.context_compiler_generator.build_generator.generator_type.value.lower(),
                runner=runner,
                generator_cmake=generator_cmake,
                c_compiler=c_cpp_compiler[0],
                cpp_compiler=c_cpp_compiler[1],
                toolset=toolset,
            )
        )
    if len(errors) > 0:
        return OrchestratorMatrixToGitHubWFExpected.make_error(errors)

    return OrchestratorMatrixToGitHubWFExpected.make_value(res)


def copy_portable_csorchestrator(output_folder: Path) -> None:

    source = files("csorchestrator").joinpath("portable")
    destination = output_folder / "csorchestratorsdk" / "portable"

    with as_file(source) as source_path:
        shutil.copytree(source_path, destination, dirs_exist_ok=True)

    readme = destination / "README.md"
    text = """
# csorchestratorsdk portable

This is the `csorchestratorsdk` portable folder.

**This folder and its contents are autogenerated.**
Do not modify files manually.
"""
    readme.write_text(
        text,
        encoding="utf-8",
    )


def create_github_wf(name: str, *, config: WorkflowTrigger) -> GitHubWorkflow:

    gwf = GitHubWorkflow(name)
    if config.on_push_branches is not None or config.on_push_tags is not None:
        gwf.on_push(branches=config.on_push_branches, tags=config.on_push_tags)
    if config.on_pull_request_branches is not None:
        gwf.on_pull_request(branches=config.on_pull_request_branches)
    if config.on_dispatch:  # not None and true
        gwf.on_dispatch()
    if config.on_schedule is not None:
        gwf.on_schedule(config.on_schedule)
    return gwf


def validate_and_generate_github_workflow(
    orchestrator: Orchestrator,
    script_folder_path: Path,
    output_path: Path | None,
    reporter: OrchestratorExecutorReporterBase,
) -> ExecutionResult:

    res = ExecutionResult()
    res.execution_description = orchestrator.extract_minimal_description()
    reporter.report_execution_description(res.execution_description)

    orchestrator_validated_opt = create_validated_orchestrator(orchestrator)
    res.report_pre_execution.append_report(orchestrator_validated_opt.main_report)
    res.report_validation = orchestrator_validated_opt.validation_reports
    reporter.report_validation_report(res.report_validation)

    if orchestrator_validated_opt.orchestrator is None:
        reporter.report_pre_execution_report(res.report_pre_execution)
        reporter.finalize_execution()
        return res

    orchestrator = orchestrator_validated_opt.orchestrator

    # validated orchestrator

    matrix = orchestrator.execution_matrix

    assert isinstance(matrix, ExecutionMatrixOsArchCompilerGenerator)  # ensured by the validator

    wf_matrix_or_errors = orchestrator_matrix_to_github_wf_matrix(matrix)
    if wf_matrix_or_errors.error is not None:
        for e in wf_matrix_or_errors.error:
            res.report_pre_execution.append_error(e)
        reporter.report_pre_execution_report(res.report_pre_execution)
        reporter.finalize_execution()
        return res

    assert wf_matrix_or_errors.value is not None
    wf_matrix = wf_matrix_or_errors.value

    if orchestrator.wf_config is None:
        res.report_pre_execution.append_error("github_workflow requires setting up the wf_config in orchestrator")
        reporter.report_pre_execution_report(res.report_pre_execution)
        reporter.finalize_execution()
        return res

    wf = create_github_wf(orchestrator.name, config=orchestrator.wf_config.trigger)

    portable_output_folder = None
    if output_path is None:
        portable_output_folder = script_folder_path
        output_path = script_folder_path / Path(".github") / Path("workflows")

    dir_creation_res = ensure_directory_exists_or_create_and_is_usable(output_path.resolve())

    if dir_creation_res.error is not None:
        res.report_pre_execution.append_error(dir_creation_res.error)
        reporter.report_pre_execution_report(res.report_pre_execution)
        reporter.finalize_execution()
        return res

    assert dir_creation_res.value
    output_folder = dir_creation_res.value
    output_path = output_folder / Path(f"{wf.name}.yml")

    # end pre execution
    reporter.report_pre_execution_report(res.report_pre_execution)

    if orchestrator.wf_config.create_release_on_tag is not None:
        # TODO: move to some configurable parameters

        release_creation_context = ReleaseCreationContext(
            orchestrator_description=orchestrator.create_orchestrator_description(),
            matrix_list=[item.original_os_architecture_compiler_generator_list for item in wf_matrix],
            script_folder_path=script_folder_path,
        )

        wf.on_job_create_release_on_tag(
            JobReleaseCreationFromArtifacts(
                config=orchestrator.wf_config.create_release_on_tag,
                needs=orchestrator.execution_matrix.name,
                release_creation_context=release_creation_context,
                runs_on="ubuntu-latest",
                if_str="${{ github.ref_type == 'tag' }}",
            )
        )

    wf_job = create_job_from_matrix_list(
        name=matrix.name,
        matrix_list=wf_matrix,
        fail_fast=matrix.fail_fast,
    )
    wf.on_job_matrix_exec(job=wf_job)

    wf_context = JobOrchestratorMatrixExecutionContext(orchestrator.create_orchestrator_description(), wf_matrix)

    reporter.report_start_execution("orchestrator execution without matrix")
    # execute the orchestrator visitor, which will execute the step to clone the repo, build, etc...
    report_execution = execute_orchestrator(
        orchestrator, OrchestratorVisitorGitHubWorkflowPreparation(wf_job, wf_context), reporter=reporter
    )
    reporter.report_execution_report(report_execution)

    res.report_executions.append(report_execution)

    lines = yaml.safe_dump(
        wf.to_dict(),
        sort_keys=False,
        default_flow_style=False,
        width=1000,  # keep a generous limit
    )

    output_path.write_text(lines, encoding="utf-8")

    if portable_output_folder is not None:
        copy_portable_csorchestrator(portable_output_folder)

    reporter.finalize_execution()

    return res
