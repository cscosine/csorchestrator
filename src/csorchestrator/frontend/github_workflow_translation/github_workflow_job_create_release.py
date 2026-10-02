from dataclasses import dataclass
from pathlib import Path
from typing import Any

from csorchestrator.domain.orchestrator.workflow_config import (
    ReleaseCreationOnTagConfigBase,
    ReleaseCreationOnTagConfigBaseCapability,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    CleanArtifactsFolder,
    CreateGitHubRelease,
    DownloadAllArtifacts,
    ShowDownloadedFiles,
    StepCheckoutRepository,
    StepGitHubUploadArtifacts,
)
from csorchestrator.frontend.github_workflow_translation.release_creation_context import ReleaseCreationContext


class ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow(ReleaseCreationOnTagConfigBaseCapability):
    # TODO: make virtual methods

    def to_steps_dict(self, release_creation_context: ReleaseCreationContext) -> list[dict[str, Any]]:
        return []

    def get_artifacts_dir(self) -> str:
        return ""

    def get_output_bundle_filename(self) -> Path:
        return Path()

    def has_additional_files_for_bundle(self) -> bool:
        return False

    def get_output_folder_for_generated_files(self) -> Path:
        return Path()

    def get_output_manifest_filename(self, project_name_and_version_string: str) -> Path:
        return Path()


@dataclass
class JobReleaseCreationFromArtifacts:
    config: ReleaseCreationOnTagConfigBase
    needs: str
    release_creation_context: ReleaseCreationContext
    runs_on: str
    if_str: str
    self_checkout_repo: bool = True

    def to_dict(self) -> dict[str, Any]:

        steps = []
        capability = self.config.get_capability(ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow)
        if capability is None:
            return {}  # this should be an error to be reported

        artifacts_dir = capability.get_artifacts_dir()
        output_bundle_file = capability.get_output_bundle_filename()
        has_additional_files_for_bundle = capability.has_additional_files_for_bundle()
        output_folder_for_generated_files = capability.get_output_folder_for_generated_files()
        output_manifest_filename = capability.get_output_manifest_filename(
            self.release_creation_context.orchestrator_description.name_and_version_string
        )

        output_manifest_path = Path(artifacts_dir) / output_folder_for_generated_files / output_manifest_filename
        output_bundle_path = Path(artifacts_dir) / output_folder_for_generated_files / output_bundle_file

        additional_files_for_release_list: list[Path] = [output_manifest_path]
        if has_additional_files_for_bundle:
            additional_files_for_release_list.append(output_bundle_path)

        if self.self_checkout_repo:
            steps += [
                StepCheckoutRepository(
                    name="Repo Self Checkout",
                ).to_dict(),
            ]

        steps += [
            # clean folder is necessary in case a second exec of the release job is required
            # e.g. a retry in case of infra issues
            CleanArtifactsFolder(artifacts_dir).to_dict(),
            DownloadAllArtifacts(artifacts_dir).to_dict(),
            ShowDownloadedFiles(artifacts_dir).to_dict(),
        ]

        steps.extend(capability.to_steps_dict(self.release_creation_context))

        steps.append(
            StepGitHubUploadArtifacts(
                name="Upload manifest as artifacts",
                with_name=output_manifest_filename.as_posix(),
                with_path=[f"{output_manifest_path.as_posix()}"],
            ).to_dict()
        )

        if has_additional_files_for_bundle:
            steps.append(
                StepGitHubUploadArtifacts(
                    name=f"Upload additional file {str(output_bundle_file)} as artifact",
                    with_name=output_bundle_file.as_posix(),
                    with_path=[f"{output_bundle_path.as_posix()}"],
                ).to_dict()
            )

        steps.append(
            CreateGitHubRelease(
                artifacts_folder=artifacts_dir,
                if_str=self.if_str,
                additional_files_list=additional_files_for_release_list,
            ).to_dict()
        )

        return {
            self.config.name: {
                "needs": self.needs,
                "runs-on": self.runs_on,
                "permissions": {"contents": "write"},
                "steps": steps,
            }
        }
