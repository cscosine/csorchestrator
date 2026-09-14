from dataclasses import dataclass, field
from pathlib import Path

from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase, StepExtra
from csorchestrator.foundation.core.report import Report
from csorchestrator.foundation.file_system.path import is_clean_relative_path
from csorchestrator.foundation.git.repo_clone_checkout import try_git_clone_checkout
from csorchestrator.foundation.git.repo_validate_and_sync import validate_and_sync_repo
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepCheckoutRepository,
    StepCheckoutRepositoryWith,
)
from csorchestrator.frontend.github_workflow_translation.matrix_execution_context import (
    JobOrchestratorMatrixExecutionContext,
)
from csorchestrator.frontend.github_workflow_translation.orchestrator_visitor_github_wf_generator import (
    OptionalListGithubStepsWithReport,
    StepCapabilityGithubWorkflow,
)
from csorchestrator.frontend.local_execution.context_local_execution import ContextLocalExecution
from csorchestrator.frontend.local_execution.orchestrator_visitor_local_executor import StepCapabilityLocalExecution
from csorchestrator.frontend.validation.orchestrator_visitor_validator import (
    StepCapabilityValidation,
    StepValidatorBase,
)


@dataclass
class StepGetRepositoryGitHubSelfCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepGetRepositoryGitHubSelf"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_get_repository_self_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepGetRepositoryGitHubSelf(StepBase):
    def __post_init__(self) -> None:
        self.add_capability(StepGetRepositoryGitHubSelfCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)


@dataclass
class StepGetRepositoryGitHubCapabilityGithubWorkflow(StepCapabilityGithubWorkflow):
    step: "StepGetRepositoryGitHub"

    def to_githubwf(
        self, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
    ) -> OptionalListGithubStepsWithReport:
        return step_get_repository_to_githubwf(self.step, wf_job, reporter_sink)


@dataclass
class StepGetRepositoryGitHubCapabilityLocalExecution(StepCapabilityLocalExecution):
    step: "StepGetRepositoryGitHub"

    def execute_locally(self, context: ContextLocalExecution, reporter_sink: ReporterSinkBase) -> Report:
        return execute_step_get_repository(self.step, context, reporter_sink)


@dataclass
class StepGetRepositoryGitHubCapabilityValidation(StepCapabilityValidation):
    @classmethod
    def create_validator(cls) -> StepValidatorBase | None:
        return StepGetRepositoryValidator()


@dataclass
class StepGetRepositoryGitHub(StepBase):
    repo_url_parts: RepoUrlParts
    repo_ref: str
    target_directory: str

    def __post_init__(self) -> None:
        self.add_capability(StepGetRepositoryGitHubCapabilityGithubWorkflow(self), StepCapabilityGithubWorkflow)
        self.add_capability(StepGetRepositoryGitHubCapabilityLocalExecution(self), StepCapabilityLocalExecution)
        self.add_capability(StepGetRepositoryGitHubCapabilityValidation(), StepCapabilityValidation)

    def repo_url(self) -> str:
        return self.repo_url_parts.repo_url()

    GITHUB_BASE_URL_SSH: str = "git@github.com:"
    GITHUB_BASE_URL_HTTPS: str = "https://github.com/"

    # note, repo_ref can be
    # - Branch, e.g. "main", "dev"
    # - Tag, e.g. "v0.0.1"
    # - Commit hash, e.g. "9f8e7d6c5b4a3210abcd1234ef56789012345678"

    def resolved_target_directory_path(self) -> Path:
        return Path(self.target_directory).resolve()


@dataclass
class StepGetRepositoryExtraAccessToken(StepExtra):
    token_name: str

    @classmethod
    def get_token_name_or_none(cls, repo_step: StepGetRepositoryGitHub) -> str | None:
        access_token_extra = repo_step.get_extra(StepGetRepositoryExtraAccessToken)
        if access_token_extra is None:
            return None

        return access_token_extra.token_name


def execute_step_get_repository(
    repo_step: StepGetRepositoryGitHub, context: ContextLocalExecution, reporter_sink: ReporterSinkBase
) -> Report:
    report = Report()

    target_full_path = context.base_folder_path / repo_step.target_directory

    if not target_full_path.is_dir():
        depth_one = StepGetRepositoryExtraDepthOne.has_depth_one_on_local_checkout(repo_step)

        report.append_info(
            f"Clone from {repo_step.repo_url()} to {target_full_path} {f'depth one? {depth_one}' if depth_one else ''}"
        )

        r_sub = try_git_clone_checkout(
            repo_url=repo_step.repo_url(),
            repo_ref=repo_step.repo_ref,
            target_path=target_full_path,
            depth_one=depth_one,
        )

        report.append_report(r_sub)

    else:
        report.append_info(
            f"Given target_directory exists, then try to update from {repo_step.repo_url()} ref {repo_step.repo_ref}"
        )

        validate_and_sync_report = validate_and_sync_repo(
            repo_url=repo_step.repo_url(), repo_ref=repo_step.repo_ref, target_path=target_full_path
        )
        report.append_report(validate_and_sync_report)

    return report


def step_get_repository_self_to_githubwf(
    step: StepGetRepositoryGitHubSelf, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:

    steps: list[GithubStepInterface] = [
        StepCheckoutRepository(
            name=step.name,
        )
    ]
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())


def step_get_repository_to_githubwf(
    step: StepGetRepositoryGitHub, wf_job: JobOrchestratorMatrixExecutionContext, reporter_sink: ReporterSinkBase
) -> OptionalListGithubStepsWithReport:
    steps: list[GithubStepInterface] = [
        StepCheckoutRepository(
            name=step.name,
            with_step=StepCheckoutRepositoryWith(
                repository=step.repo_url_parts.repo_org_name_sub_url(),
                path=step.target_directory,
                ref=step.repo_ref,
                fetch_depth="1"
                if StepGetRepositoryExtraDepthOne.has_depth_one_on_github_action_checkout(step)
                else None,
                token=StepGetRepositoryExtraAccessToken.get_token_name_or_none(step),
            ),
        )
    ]
    return OptionalListGithubStepsWithReport.create_result_and_report(steps, Report())


def validate_step_get_repository(step: StepGetRepositoryGitHub) -> Report:
    report = Report()

    if not is_clean_relative_path(step.target_directory, avoid_leaving_base=True):
        report.append_error(
            f"Invalid target_directory {step.target_directory}, it must be a clean relative path that "
            "does not leave the base folder"
        )

    return report


@dataclass
class StepGetRepositoryValidator(StepValidatorBase):
    _collected_step_get_repository_target_directories: set[Path] = field(default_factory=set)

    def validate(self, step: StepBase) -> Report:
        if not isinstance(step, StepGetRepositoryGitHub):
            r = Report()
            r.append_error(f"expected StepGetRepositoryGitHub, got {type(step).__name__}")
            return r

        return self._validate_step_get_repository(step)

    def _validate_step_get_repository(self, step: StepGetRepositoryGitHub) -> Report:
        r = validate_step_get_repository(step)
        if not r.has_errors():
            target_directory_path = step.resolved_target_directory_path()
            if target_directory_path in self._collected_step_get_repository_target_directories:
                r.append_error(f"target_directory {str(target_directory_path)} is already used by another step")
            else:
                self._collected_step_get_repository_target_directories.add(target_directory_path)
        return r


@dataclass
class StepGetRepositoryExtraDepthOne(StepExtra):
    on_local_checkout: bool
    on_github_action_checkout: bool

    @classmethod
    def has_depth_one_on_local_checkout(cls, repo_step: StepGetRepositoryGitHub) -> bool:
        depth_one_only = False
        depth_one_extra_opt = repo_step.get_extra(StepGetRepositoryExtraDepthOne)
        if depth_one_extra_opt is not None:
            depth_one_only = depth_one_extra_opt.on_local_checkout
        return depth_one_only

    @classmethod
    def has_depth_one_on_github_action_checkout(cls, repo_step: StepGetRepositoryGitHub) -> bool:
        depth_one_only = False
        depth_one_extra_opt = repo_step.get_extra(StepGetRepositoryExtraDepthOne)
        if depth_one_extra_opt is not None:
            depth_one_only = depth_one_extra_opt.on_github_action_checkout
        return depth_one_only
