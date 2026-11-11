import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
    create_header_only_variant_string,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
from csorchestrator.foundation.core.report import Report
from csorchestrator.foundation.file_system.directory import (
    ensure_directory_exists_or_create_and_is_usable,
)
from csorchestrator.frontend.github_workflow_translation.github_step_interface import (
    GithubStepInterface,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    MatrixOsArchCompilerGeneratorGithubConstants,
    create_context_os_architecture_compiler_generator_string_github_matrix,
    create_header_only_variant_string_github_matrix,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepRunCommand,
)
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
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import (
    StepCapabilityLocalExecution,
)
from csorchestrator.frontend.step.github_release_download import (
    DownloadGithubFileEntry,
    download_and_extract_github_release_asset,
    github_release_download_and_extract_steps,
)
from csorchestrator.frontend.step.step_get_repository import StepGetRepositoryGitHub
from csorchestrator.portable.release_manifest import create_archive_filename


@dataclass
class StepGetPrecompiledLibGithubCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepGetPrecompiledLibGithub"

    def to_githubwf(
        self,
        wf_job: JobOrchestratorMatrixExecutionContext,
        reporter_sink: ReporterSinkBase,
    ) -> OptionalListGithubStepsWithReport:
        return step_get_precompiled_lib_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepGetPrecompiledLibGithubCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepGetPrecompiledLibGithub"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_get_precompiled_lib(self.step, context, reporter_sink)


MappingFunction = Callable[
    [ContextOsArchitectureCompilerGenerator],
    ContextOsArchitectureCompilerGenerator | None,
]


def identity_mapping_function(
    context: ContextOsArchitectureCompilerGenerator,
) -> ContextOsArchitectureCompilerGenerator | None:
    return context


# h = compose(f, g)  f(g(x))
def compose_mapping_function(
    f: MappingFunction,
    g: MappingFunction,
) -> MappingFunction:
    def composed(
        context: ContextOsArchitectureCompilerGenerator,
    ) -> ContextOsArchitectureCompilerGenerator | None:
        intermediate = g(context)
        if intermediate is None:
            return None
        return f(intermediate)

    return composed


@dataclass
class StepGetPrecompiledLibGithub(StepBase):
    base_url: str
    org: str
    git_repo: str
    project_name: str
    project_version: str
    project_tag: str
    lib_name: str
    lib_version: str
    base_libs_dir: Path
    headers_only: bool
    mapping_function: MappingFunction

    def __post_init__(self) -> None:
        self.add_capability(
            StepGetPrecompiledLibGithubCapabilityGithubWorkflow(self),
            StepCapabilityGithubWorkflow,
        )
        self.add_capability(
            StepGetPrecompiledLibGithubCapabilityLocalExecution(self),
            StepCapabilityLocalExecution,
        )

    GITHUB_BASE_URL_HTTPS: str = StepGetRepositoryGitHub.GITHUB_BASE_URL_HTTPS

    # TODO for private repo, will need to use API url and a api request to download, using a toke,
    # with keyring in local and token in github


def execute_step_get_precompiled_lib(
    step: StepGetPrecompiledLibGithub,
    context: ContextLocalExecution,
    reporter_sink: ReporterSinkBase,
) -> Report:
    report = Report()

    input_context_string = create_context_os_architecture_compiler_generator_string(
        context.get_active_os_architecture_compiler_generator()
    )

    if step.mapping_function == identity_mapping_function:
        if step.headers_only:
            source_lib_variant = create_header_only_variant_string(
                context.get_active_os_architecture_compiler_generator().context_os_architecture.os
            )
            release_name_part = source_lib_variant
        else:
            release_name_part = input_context_string
    else:
        # first apply mapping functiont --> eg. map linux-clang to linux-gcc
        source_context = step.mapping_function(deepcopy(context.get_active_os_architecture_compiler_generator()))
        if source_context is None:
            report.append_error(f"mapping function returned None for input context {input_context_string}")
            return report

        # then apply header only on the resulting context
        if step.headers_only:
            source_lib_variant = create_header_only_variant_string(source_context.context_os_architecture.os)
            release_name_part = source_lib_variant
        else:
            release_name_part = create_context_os_architecture_compiler_generator_string(source_context)

    libs_subdir_path: Path = context.base_folder_path / step.base_libs_dir / input_context_string

    dir_creation_res = ensure_directory_exists_or_create_and_is_usable(libs_subdir_path.resolve())

    if dir_creation_res.error is not None:
        report.append_error(dir_creation_res.error)
        return report

    assert dir_creation_res.value is not None
    target_dir = dir_creation_res.value

    filename = create_archive_filename(
        project_name_and_version=Orchestrator.compose_name_version_to_string(step.project_name, step.project_version),
        context_os_architecture_compiler_generator_string=release_name_part,
        lib_name=step.lib_name,
        lib_version=step.lib_version,
    )

    fe = DownloadGithubFileEntry(
        base_url=step.base_url,
        org=step.org,
        git_repo=step.git_repo,
        tag=step.project_tag,
        asset_filename=filename,
    )

    report.append_report(download_and_extract_github_release_asset(fe, target_dir))
    return report


def sanitize_github_identifier(value: str) -> str:
    # Replace invalid chars with underscore
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)

    # Avoid empty string
    if not value:
        value = "_"

    # Optional: avoid starting with a digit
    if value[0].isdigit():
        value = "_" + value

    return value


def step_get_precompiled_lib_to_githubwf(
    step: StepGetPrecompiledLibGithub,
    wf_job: JobOrchestratorMatrixExecutionContext,
    reporter_sink: ReporterSinkBase,
) -> OptionalListGithubStepsWithReport:

    release_name_part = create_context_os_architecture_compiler_generator_string_github_matrix()
    input_context_string = step.base_libs_dir / release_name_part

    steps: list[GithubStepInterface] = []

    if step.mapping_function == identity_mapping_function:
        if step.headers_only:
            source_lib_variant = create_header_only_variant_string_github_matrix()
            release_name_part = source_lib_variant
        # else: release_name_part is ok!

        src_filename = create_archive_filename(
            project_name_and_version=Orchestrator.compose_name_version_to_string(
                step.project_name, step.project_version
            ),
            context_os_architecture_compiler_generator_string=release_name_part,
            lib_name=step.lib_name,
            lib_version=step.lib_version,
        )

        asset_filename = src_filename

    else:
        # mapping needs two steps, one to prepare a dict of valid entries corresponding to execution matrix id,
        # and then one to download the selected one
        step_id = sanitize_github_identifier(f"filename_{step.project_name}_{step.lib_name}")
        filename_variable = f"{step_id}"

        filenames_dict_lines: list[str] = []
        if step.headers_only:
            # if headers only, first apply mapping, then headers only resolution
            for matrix_id, matrix in enumerate(wf_job.matrix_includes):
                new_context = step.mapping_function(deepcopy(matrix.original_os_architecture_compiler_generator_list))
                if new_context is None:
                    return OptionalListGithubStepsWithReport.create_report(
                        Report().append_error(
                            f"error evaluating mapping function for {step.name} in github translation"
                        )
                    )
                filenames_dict_lines += [
                    f'    {matrix_id}: "{create_header_only_variant_string(new_context.context_os_architecture.os)}",',
                ]
        else:
            for matrix_id, matrix in enumerate(wf_job.matrix_includes):
                new_context = step.mapping_function(deepcopy(matrix.original_os_architecture_compiler_generator_list))
                if new_context is None:
                    return OptionalListGithubStepsWithReport.create_report(
                        Report().append_error(
                            f"error evaluating mapping function for {step.name} in github translation"
                        )
                    )
                filenames_dict_lines += [
                    f'    {matrix_id}: "{create_context_os_architecture_compiler_generator_string(new_context)}",',
                ]

        run_list = [
            "import os",
            "import sys",
            "from csorchestratorsdk.portable.release_manifest import create_archive_filename",
            "",
            f'execution_id = int("{MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_EXECUTION_ID_EMBRACED}")',
            "",
            "filenames = {",
        ]
        run_list += filenames_dict_lines
        run_list += [
            "}",
            "",
            "if execution_id not in filenames:",
            '    print("Unsupported matrix entry")',
            "    sys.exit(1)",
            "",
            "filename = create_archive_filename(",
            f"    project_name_and_version='{step.project_name}-{step.project_version}',",
            "    context_os_architecture_compiler_generator_string=filenames[execution_id],",
            f"    lib_name='{step.lib_name}',",
            f"    lib_version='{step.lib_version}',",
            ")",
            'with open(os.environ["GITHUB_OUTPUT"], "a") as f:',
            f'    f.write(f"{filename_variable}={{filename}}\\n")',
        ]

        steps.append(
            StepRunCommand(
                name=step.name + " prepare filename",
                id=step_id,
                shell_type="python",
                run=run_list,
                env={"PYTHONPATH": "${{ github.workspace }}"},
            )
        )

        asset_filename = f"${{{{ steps.{step_id}.outputs.{filename_variable} }}}}"

    # finally, download and extract the archive
    steps += github_release_download_and_extract_steps(
        name=step.name,
        entry=DownloadGithubFileEntry(
            base_url=step.base_url,
            org=step.org,
            git_repo=step.git_repo,
            tag=step.project_tag,
            asset_filename=asset_filename,
        ),
        target_dir=input_context_string.as_posix(),
    )
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
