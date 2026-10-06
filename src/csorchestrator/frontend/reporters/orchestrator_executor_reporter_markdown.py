from dataclasses import dataclass, field
from pathlib import Path

from csorchestrator.domain.orchestrator.orchestrator_executor_reporter_base import OrchestratorExecutorReporterBase
from csorchestrator.domain.orchestrator.orchestrator_minimal_description import OrchestratorExecutorMinimalDescription
from csorchestrator.domain.orchestrator.orchestrator_visitor_base import OrchestratorExecutorVisitReports
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.reporters.report_reporter import repo_to_reporter_sink
from csorchestrator.frontend.reporters.reporter_sink_markdown_file import ReporterSinkMarkdown


@dataclass
class OrchestratorExecutorReporterMarkdown(OrchestratorExecutorReporterBase):
    path: Path
    sink: ReporterSinkMarkdown = field(init=False)

    def __post_init__(self) -> None:
        self.sink = ReporterSinkMarkdown()

    # ---------------- VISIT ----------------

    def on_init_visit(self) -> None:
        self.sink.lines.append("# Orchestrator Execution Report\n")

    def on_end_visit(self, visit_complete: bool) -> None:
        status = "SUCCESS" if visit_complete else "FAILURE"
        self.sink.lines.append(f"\n## End Visit: {status}\n")

    def finalize_execution(self) -> None:
        self.save()

    # ---------------- PHASE ----------------

    def on_begin_phase(self, phase: Phase) -> None:
        self.sink.lines.append(f"\n## Phase: {phase.name}\n")

    def on_end_phase(self, phase_complete: bool) -> None:
        self.sink.lines.append(f"\n**Phase result:** {'OK' if phase_complete else 'FAIL'}\n")

    # ---------------- STEP ----------------

    def create_sink_on_begin_visit_step(self, step: StepBase) -> ReporterSinkBase:
        self.sink.lines.append(f"\n### Step: {step.name}\n")
        self.sink.increase_indentation()
        return self.sink

    def on_end_visit_step(self, step: StepBase, report: Report) -> None:
        if report.has_errors():
            self.sink.lines.append(f"❌ Step {step.name} FAILED\n")
        else:
            self.sink.lines.append(f"✔ Step {step.name} OK\n")

        repo_to_reporter_sink(report, self.sink)
        self.sink.decrease_indentation()

    # ---------------- POST EXECUTION ----------------

    def report_postexecution(self, report: Report) -> None:
        if report.has_errors():
            self.sink.lines.append("❌ Post execution FAILED\n")
        else:
            self.sink.lines.append("✔ Post execution OK\n")

        self.sink.increase_indentation()
        repo_to_reporter_sink(report, self.sink)
        self.sink.decrease_indentation()

    # ---------------- CREATION ----------------

    def report_orchestrator_creation_report(self, report: Report) -> None:
        self.sink.lines.append("## Creation Report\n")
        repo_to_reporter_sink(report, self.sink)

    # ---------------- EXECUTION DESCRIPTION ----------------

    def report_execution_description(
        self,
        execution_description: OrchestratorExecutorMinimalDescription,
    ) -> None:
        self.sink.lines.append("## Execution Description\n")

        for phase_desc in execution_description.phases_and_steps:
            self.sink.lines.append(f"### Phase: {phase_desc.phase_name}")
            for step_name in phase_desc.step_names:
                self.sink.lines.append(f"- Step: {step_name}")

        if len(execution_description.matrix_description) > 0:
            self.sink.lines.append("### Execution Matrix")
            for line in execution_description.matrix_description:
                self.sink.lines.append(f"- {line}")

    # ---------------- PRE EXECUTION ----------------

    def report_pre_execution_report(self, report: Report) -> None:
        self.sink.lines.append("## Pre-Execution Report\n")
        repo_to_reporter_sink(report, self.sink)

    def report_validation_report(self, report: OrchestratorExecutorVisitReports) -> None:
        self.sink.lines.append("## Validation Report\n")

        for phase_report in report:
            self.sink.increase_indentation()
            for step_report in phase_report:
                self.sink.increase_indentation()
                repo_to_reporter_sink(step_report, self.sink)
                self.sink.decrease_indentation()
            self.sink.decrease_indentation()

    # ---------------- EXECUTION REPORT ----------------

    def report_start_execution(self, exec_desc: str) -> None:
        self.sink.lines.append(f"## Start Execution {exec_desc}\n")

    def report_skip_execution(self, exec_desc: str) -> None:
        self.sink.lines.append(f"## Skip Execution {exec_desc}\n")

    def report_execution_report(self, report_visit: OrchestratorExecutorVisitReports) -> None:
        self.sink.lines.append("## Execution Report\n")

        for phase_report in report_visit:
            self.sink.increase_indentation()
            for step_report in phase_report:
                self.sink.increase_indentation()
                repo_to_reporter_sink(step_report, self.sink)
                self.sink.decrease_indentation()
            self.sink.decrease_indentation()

    # ---------------- SAVE ----------------

    def save(self) -> None:
        self.path.write_text("\n".join(self.sink.lines), encoding="utf-8")
