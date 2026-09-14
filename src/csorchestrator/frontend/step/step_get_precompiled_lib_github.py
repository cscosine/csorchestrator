import os
import re
import tarfile
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
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
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepGitHubAction,
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
    mapping_function: MappingFunction | None = None

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

    libs_subdir = create_context_os_architecture_compiler_generator_string(
        context.get_active_os_architecture_compiler_generator()
    )

    if step.mapping_function is None:
        release_name_part = libs_subdir
    else:
        source_context = step.mapping_function(deepcopy(context.get_active_os_architecture_compiler_generator()))
        if source_context is None:
            report.append_error(f"mapping function returned None for input context {libs_subdir}")
            return report

        release_name_part = create_context_os_architecture_compiler_generator_string(source_context)

    libs_subdir_path: Path = context.base_folder_path / step.base_libs_dir / libs_subdir

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
    source_filename = filename
    target_filename = target_dir / filename

    download_url = urljoin(
        step.base_url,
        "/".join(
            [
                step.org,
                step.git_repo,
                "releases",
                "download",
                step.project_tag,
                source_filename,
            ]
        ),
    )
    report.append_info("download URL " + download_url + " to " + target_filename.as_posix())

    # download
    try:
        request.urlretrieve(download_url, target_filename)
    except HTTPError as e:
        report.append_error(f"HTTP error: {e.code} - {e.reason}")
        return report

    except URLError as e:
        report.append_error(f"Network error: {e.reason}")
        return report

    # Check file exists and is not empty
    if not os.path.exists(target_filename):
        report.append_error("Download failed: file does not exist")
        return report

    if os.path.getsize(target_filename) == 0:
        report.append_error("Download failed: file is empty")
        return report

    # extract
    if not tarfile.is_tarfile(target_filename):
        report.append_error("Downloaded file is not a valid tar archive")
        return report

    try:
        with tarfile.open(target_filename, "r:gz") as tar:
            tar.extractall(target_dir)
    except tarfile.ReadError:
        report.append_error("Extraction failed: corrupted tar.gz file")
        return report

    # Delete archive
    os.remove(target_filename)

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
    libs_subdir = step.base_libs_dir / release_name_part

    steps: list[GithubStepInterface] = []

    if step.mapping_function is None:
        src_filename = create_archive_filename(
            project_name_and_version=Orchestrator.compose_name_version_to_string(
                step.project_name, step.project_version
            ),
            context_os_architecture_compiler_generator_string=release_name_part,
            lib_name=step.lib_name,
            lib_version=step.lib_version,
        )

        steps.append(
            StepGitHubAction(
                name=step.name + " download tar.gz",
                uses="robinraju/release-downloader@v1.13",
                with_list={
                    "repository": f"{step.org}/{step.git_repo}",
                    "tag": f"{step.project_tag}",
                    "fileName": f"{src_filename}",
                    "out-file-path": f"{libs_subdir.as_posix()}",
                },
            )
        )

        tarfile_path = libs_subdir / f"{src_filename}"

    else:
        # mapping needs two steps, one to prepare a dict of valid entries corresponding to execution matrix id,
        # and then one to download the selected one
        step_id = sanitize_github_identifier(f"filename_{step.project_name}_{step.lib_name}")
        filename_variable = f"{step_id}"

        filenames_dict_lines: list[str] = []
        for matrix_id, matrix in enumerate(wf_job.matrix_includes):
            new_context = step.mapping_function(deepcopy(matrix.original_os_architecture_compiler_generator_list))
            if new_context is None:
                return OptionalListGithubStepsWithReport.create_report(
                    Report().append_error(f"error evaluating mapping function for {step.name} in github translation")
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

        steps.append(
            StepGitHubAction(
                name=step.name + " download tar.gz",
                uses="robinraju/release-downloader@v1.13",
                with_list={
                    "repository": f"{step.org}/{step.git_repo}",
                    "tag": f"{step.project_tag}",
                    "fileName": f"${{{{ steps.{step_id}.outputs.{filename_variable} }}}}",
                    "out-file-path": f"{libs_subdir.as_posix()}",
                },
            )
        )

        tarfile_path = libs_subdir / f"${{{{ steps.{step_id}.outputs.{filename_variable} }}}}"

    # finally, one step to extract the archive

    steps.append(
        StepRunCommand(
            name=step.name + " extract tar.gz",
            shell_type="bash",
            run=[
                f"tar -xzf {tarfile_path.as_posix()} -C {libs_subdir.as_posix()}",
                f"rm -f {tarfile_path.as_posix()}",
            ],
        )
    )
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())
