from dataclasses import dataclass
from pathlib import Path
from typing import Any

from csorchestrator.domain.orchestrator.workflow_config import (
    ReleaseCreationOnTagConfigBase,
    ReleaseCreationOnTagConfigBaseCapability,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    CreateGitHubRelease,
    DownloadAllArtifacts,
    ShowDownloadedFiles,
    StepCheckoutRepository,
    StepGitHubUploadArtifacts,
)
from csorchestrator.frontend.github_workflow_translation.release_creation_context import ReleaseCreationContext
from csorchestrator.portable.release_manifest import ReleaseManifest


class ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow(ReleaseCreationOnTagConfigBaseCapability):
    # TODO: make virtual methods

    def to_steps_dict(self, release_creation_context: ReleaseCreationContext) -> list[dict[str, Any]]:
        return []

    def get_artifacts_dir(self) -> str:
        return ""

    def get_output_bundle_filename(self) -> Path | None:
        return None


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

        if self.self_checkout_repo:
            steps += [
                StepCheckoutRepository(
                    name="Repo Self Checkout",
                ).to_dict(),
            ]

        steps += [
            DownloadAllArtifacts(artifacts_dir).to_dict(),
            ShowDownloadedFiles(artifacts_dir).to_dict(),
        ]

        output_bundle_file = None

        capability = self.config.get_capability(ReleaseCreationOnTagConfigBaseCapabilityGithubWorkflow)
        extra_extension_for_release_files = None
        if capability is not None:
            steps.extend(capability.to_steps_dict(self.release_creation_context))
            extra_extension_for_release_files = ReleaseManifest.CSORCHESTRATOR_MANIFEST_EXTENSION
            steps.append(
                StepGitHubUploadArtifacts(
                    name="Upload manifest as artifacts",
                    with_name="manifest" + extra_extension_for_release_files,
                    with_path=[f"{artifacts_dir}/**/*{extra_extension_for_release_files}"],
                ).to_dict()
            )

            output_bundle_file = capability.get_output_bundle_filename()
            if output_bundle_file is not None:
                steps.append(
                    StepGitHubUploadArtifacts(
                        name=f"Upload additional file {str(output_bundle_file)} as artifact",
                        with_name=output_bundle_file.as_posix(),
                        with_path=[f"{artifacts_dir}/{output_bundle_file.as_posix()}"],
                    ).to_dict()
                )

        steps.append(
            CreateGitHubRelease(
                artifacts_folder=artifacts_dir,
                if_str=self.if_str,
                extra_extension_for_release_files=extra_extension_for_release_files,
                additional_files_list=[output_bundle_file] if output_bundle_file is not None else [],
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
