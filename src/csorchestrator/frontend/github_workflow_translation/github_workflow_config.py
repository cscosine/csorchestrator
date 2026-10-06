from dataclasses import dataclass, field
from typing import Any, Self

from csorchestrator.domain.orchestrator.workflow_config import Cron
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_create_release import (
    JobReleaseCreationFromArtifacts,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_job_matrix_execution import (
    JobOrchestratorMatrixExecution,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_triggers import (
    PullRequestTrigger,
    PushTrigger,
    ScheduleTrigger,
    TriggerInterface,
    TriggerType,
    WorkflowDispatchTrigger,
)


@dataclass
class GitHubWorkflow:
    name: str
    _on: dict[str, TriggerInterface] = field(default_factory=dict)
    _jobs_matrix_exec: list[JobOrchestratorMatrixExecution] = field(default_factory=list)
    _jobs_release_on_tag: list[JobReleaseCreationFromArtifacts] = field(default_factory=list)

    # ---------------- PUSH ----------------

    def on_push(
        self,
        *,
        branches: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Self:
        self._on[TriggerType.PUSH] = PushTrigger(branches, tags)
        return self

    # ---------------- PR ----------------

    def on_pull_request(
        self,
        *,
        branches: list[str] | None = None,
    ) -> Self:
        self._on[TriggerType.PULL_REQUEST] = PullRequestTrigger(branches)
        return self

    # ---------------- DISPATCH ----------------

    def on_dispatch(self) -> Self:
        self._on[TriggerType.WORKFLOW_DISPATCH] = WorkflowDispatchTrigger()
        return self

    # ---------------- SCHEDULE ----------------

    def on_schedule(self, cron: Cron) -> Self:
        self._on[TriggerType.SCHEDULE] = ScheduleTrigger(cron)
        return self

    # ---------------- SCHEDULE ----------------
    def on_job_matrix_exec(self, job: JobOrchestratorMatrixExecution) -> Self:
        self._jobs_matrix_exec.append(job)
        return self

    def on_job_create_release_on_tag(self, job: JobReleaseCreationFromArtifacts) -> Self:
        self._jobs_release_on_tag.append(job)
        return self

    # ---------------- OUTPUT ----------------

    def to_dict(self) -> dict[str, Any]:
        ret: dict[str, Any] = {}
        ret["name"] = self.name
        ret["on"] = {key: value for trigger in self._on.values() for key, value in trigger.to_dict().items()}
        if len(self._jobs_matrix_exec) > 0 or len(self._jobs_release_on_tag) > 0:
            release_jobs = {key: value for job in self._jobs_release_on_tag for key, value in job.to_dict().items()}
            matrix_jobs = {key: value for job in self._jobs_matrix_exec for key, value in job.to_dict().items()}
            jobs = release_jobs | matrix_jobs
            ret["jobs"] = jobs
        return ret
