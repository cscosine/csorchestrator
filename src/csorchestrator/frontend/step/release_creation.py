from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.domain.orchestrator.workflow_config import (
    ReleaseCreationOnTagConfigBase,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_create_release import (
    ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import StepRunCommand
from csorchestrator.frontend.github_workflow_translation.release_creation_context import ReleaseCreationContext
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import (
    ReleaseCreationOnTagConfigBaseCapabilityLocalExecution,
)
from csorchestrator.frontend.local_execution.release_creation_context_local_execution import (
    ReleaseCreationContextLocalExecution,
)
from csorchestrator.frontend.local_execution.validate_and_execute import create_context_os_architecture_string
from csorchestrator.frontend.step.step_get_versions_from_cmake_config_package_version import (
    create_version_file_name,
)
from csorchestrator.frontend.step.templates.utils import (
    fix_path_repr,
    relocate_portable_imports,
    replace_template_variable,
)
from csorchestrator.portable.release_manifest import (
    ReleaseManifest,
    collect_release_manifest_single_variant_and_prepare_manifest,
)


@dataclass
class ReleaseCreationOnTagConfigCapabilityGithubWorkflow(ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow):
    step: "ReleaseCreationOnTagConfig"

    def to_steps_dict(self, release_creation_context: ReleaseCreationContext) -> list[dict[str, Any]]:
        return release_creation_on_tag_config_to_githubwf(self.step, release_creation_context)

    def get_artifacts_dir(self) -> str:
        return self.step.artifacts_dir

    def get_output_bundle_filename(self) -> Path | None:
        if len(self.step.additional_files_list) > 0:
            return self.step.output_bundle_file_name
        return None


@dataclass
class ReleaseCreationOnTagConfiCapabilityLocalExecution(ReleaseCreationOnTagConfigBaseCapabilityLocalExecution):
    step: "ReleaseCreationOnTagConfig"

    def execute_locally(self, context: ReleaseCreationContextLocalExecution) -> Report:
        return release_creation_on_tag_config_execute_local(self.step, context)


@dataclass
class ReleaseCreationOnTagConfig(ReleaseCreationOnTagConfigBase):
    base_install_dir: Path  # used only in local executions, not in github wf where artifacts are downloaded
    artifacts_dir: str  # used only in github execution, specfify folders where artifacts are downloaded
    additional_files_list: list[Path]  # list of additional files
    output_bundle_file_name: Path

    def __post_init__(self) -> None:
        self.add_capability(
            ReleaseCreationOnTagConfigCapabilityGithubWorkflow(self),
            ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow,
        )
        self.add_capability(
            ReleaseCreationOnTagConfiCapabilityLocalExecution(self),
            ReleaseCreationOnTagConfigBaseCapabilityLocalExecution,
        )


def release_creation_on_tag_config_to_githubwf(
    step: ReleaseCreationOnTagConfig, release_creation_context: ReleaseCreationContext
) -> list[dict[str, Any]]:

    input_manifest_path_variant: list[tuple[Path, str]] = []
    for context in release_creation_context.matrix_list:
        context_os_architecture_compiler_generator_string = create_context_os_architecture_compiler_generator_string(
            context
        )
        input_path = Path(
            Path(
                release_creation_context.orchestrator_description.name_and_version_string
                + "-"
                + context_os_architecture_compiler_generator_string
            )
            / Path(
                create_version_file_name(
                    release_creation_context.orchestrator_description.name_and_version_string,
                    context_os_architecture_compiler_generator_string,
                )
            )
        )

        input_manifest_path_variant.append((input_path, context_os_architecture_compiler_generator_string))

    output_filepath = Path(
        f"{release_creation_context.orchestrator_description.name_and_version_string}{ReleaseManifest.CS_ORCHESTRATOR_MANIFEST_EXTENSION}"
    )

    template_file = files("csorchestrator.frontend.step").joinpath("templates").joinpath("create_release_manifest.py")
    python_code = template_file.read_text(encoding="utf-8")

    python_code = relocate_portable_imports(python_code)

    python_code = replace_template_variable(
        python_code, "input_manifest_path_variant", fix_path_repr(repr(input_manifest_path_variant))
    )
    python_code = replace_template_variable(python_code, "output_filepath", fix_path_repr(repr(output_filepath)))
    python_code = replace_template_variable(
        python_code, "project_name", repr(release_creation_context.orchestrator_description.orchestrator_name)
    )
    python_code = replace_template_variable(
        python_code, "project_version", repr(release_creation_context.orchestrator_description.orchestrator_version)
    )

    python_code = replace_template_variable(
        python_code, "base_path_additional_files", 'Path(os.environ["GITHUB_WORKSPACE"])'
    )
    python_code = replace_template_variable(
        python_code, "list_additional_files", fix_path_repr(repr(step.additional_files_list))
    )
    python_code = replace_template_variable(
        python_code,
        "output_folder_additional_files",
        fix_path_repr(repr(Path("./"))),  # this is executed in artifacts folder
    )
    python_code = replace_template_variable(
        python_code, "output_bundle_file_name", fix_path_repr(repr(step.output_bundle_file_name))
    )

    python_lines = python_code.splitlines()

    step_github = StepRunCommand(
        name="Manifest creation",
        run=python_lines,
        shell_type="python",
        working_directory=step.artifacts_dir,
        env={"PYTHONPATH": "${{ github.workspace }}"},
    )

    return [
        step_github.to_dict(),
    ]


def release_creation_on_tag_config_execute_local(
    step: ReleaseCreationOnTagConfig, relase_context: ReleaseCreationContextLocalExecution
) -> Report:
    report = Report()

    # collect all input manifest for each variant
    input_manifest_path_variant: list[tuple[Path, str]] = []
    for counter, os_architecture_compiler_generator in enumerate(
        relase_context.os_architecture_compiler_generator_list
    ):
        match = os_architecture_compiler_generator.context_os_architecture.can_be_executed_on(
            relase_context.os_architecture
        )
        if not match:
            report.append_info(
                "skip release creation on not compatible matrix config: "
                f"{create_context_os_architecture_compiler_generator_string(os_architecture_compiler_generator)}"
                ", current os and architecture:  "
                f"{create_context_os_architecture_string(relase_context.os_architecture)}"
            )
            continue
        # use the compatible os_architecture, not the detected one.
        # e.g. detected os is win 11, but we select win 10 in the matrix, which is compatible

        context = ContextLocalExecution(
            orchestrator_description=relase_context.orchestrator_description,
            base_folder_path=relase_context.base_path,
            script_folder_path=relase_context.script_folder_path,
            os_architecture=os_architecture_compiler_generator.context_os_architecture,
            active_compiler_generator=os_architecture_compiler_generator.context_compiler_generator,
            matrix_extras={},
            matrix_execution_id=str(counter),
        )

        context_os_architecture_compiler_generator_string = create_context_os_architecture_compiler_generator_string(
            context.get_active_os_architecture_compiler_generator()
        )

        input_base_dir = Path(context.base_folder_path / step.base_install_dir).resolve()
        input_full_path = Path(
            input_base_dir
            / Path(
                create_version_file_name(
                    relase_context.orchestrator_description.name_and_version_string,
                    context_os_architecture_compiler_generator_string,
                )
            )
        ).resolve()
        input_manifest_path_variant.append((input_full_path, context_os_architecture_compiler_generator_string))

    output_filepath = step.base_install_dir / Path(
        relase_context.orchestrator_description.name_and_version_string
        + ReleaseManifest.CS_ORCHESTRATOR_MANIFEST_EXTENSION
    )

    base_path_additional_files = relase_context.script_folder_path

    # TODO check they are relative and not leaving the folder
    list_additional_files = step.additional_files_list

    output_folder_additional_files = step.base_install_dir

    errors = collect_release_manifest_single_variant_and_prepare_manifest(
        input_manifest_path_variant=input_manifest_path_variant,
        output_filepath=output_filepath,
        project_name=relase_context.orchestrator_description.orchestrator_name,
        project_version=relase_context.orchestrator_description.orchestrator_version,
        base_path_additional_files=base_path_additional_files,
        list_additional_files=list_additional_files,
        output_folder_additional_files=output_folder_additional_files,
        output_bundle_file_name=step.output_bundle_file_name,
    )
    if len(errors) > 0:
        for e in errors:
            report.append_error(e)
    else:
        report.append_info(f"release manifest written to {str(output_filepath)}")

    return report
