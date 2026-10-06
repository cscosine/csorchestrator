from dataclasses import dataclass, field

from csorchestrator.domain.orchestrator.orchestrator_executor_reporter_base import OrchestratorExecutorReporterBase
from csorchestrator.domain.orchestrator.orchestrator_minimal_description import OrchestratorExecutorMinimalDescription
from csorchestrator.domain.orchestrator.orchestrator_visitor_base import OrchestratorExecutorVisitReports
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.domain.orchestrator.reporter_sink_base import ReporterSinkBase
from csorchestrator.domain.orchestrator.step_base import StepBase
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.reporters.report_reporter import repo_to_reporter_sink
from csorchestrator.frontend.reporters.reporter_sink_print import ReporterSinkPrint, ReporterSinkPrintBase


@dataclass
class OrchestratorExecutorReporterPrint(OrchestratorExecutorReporterBase):
    reporter_sink: ReporterSinkPrintBase = field(default_factory=ReporterSinkPrint)

    def on_init_visit(self) -> None:
        self.reporter_sink.stdout("[init visit]")

    def finalize_execution(self) -> None:
        pass

    def report_postexecution(self, report: Report) -> None:
        if not report.has_errors():
            self.reporter_sink.stdout("[Post execution OK]")
        else:
            self.reporter_sink.stdout("[Post execution FAIL]")

        self.reporter_sink.increase_indentation()
        repo_to_reporter_sink(report, self.reporter_sink)
        self.reporter_sink.decrease_indentation()

    def on_end_visit(self, visit_complete: bool) -> None:
        if visit_complete:
            self.reporter_sink.stdout("[end visit OK]")
        else:
            self.reporter_sink.stdout("[end visit FAIL]")
        self.reporter_sink.reset_indentation()

    def on_begin_phase(self, phase: Phase) -> None:
        self.reporter_sink.increase_indentation()
        self.reporter_sink.stdout(f"[init phase {phase.name}]")

    def on_end_phase(self, phase_complete: bool) -> None:
        if phase_complete:
            self.reporter_sink.stdout("[end phase OK]")
        else:
            self.reporter_sink.stdout("[end phase FAIL]")
        self.reporter_sink.decrease_indentation()

    def create_sink_on_begin_visit_step(self, step: StepBase) -> ReporterSinkBase:
        self.reporter_sink.increase_indentation()
        self.reporter_sink.stdout(f"[init step {step.name}]")
        return self.reporter_sink

    def on_end_visit_step(self, step: StepBase, report: Report) -> None:
        if not report.has_errors():
            self.reporter_sink.stdout(f"[end step {step.name} OK]")
        else:
            self.reporter_sink.stdout(f"[end step {step.name} FAIL]")

        self.reporter_sink.stdout(f"[{step.name} REPORT]")
        self.reporter_sink.increase_indentation()
        repo_to_reporter_sink(report, self.reporter_sink)
        self.reporter_sink.decrease_indentation()

        # end step indent
        self.reporter_sink.decrease_indentation()

    def report_orchestrator_creation_report(self, report: Report) -> None:
        self.reporter_sink.stdout("[Creation Report]")
        self.reporter_sink.increase_indentation()
        repo_to_reporter_sink(report, self.reporter_sink)
        self.reporter_sink.decrease_indentation()

    def report_execution_description(self, execution_description: OrchestratorExecutorMinimalDescription) -> None:
        for phase_desc in execution_description.phases_and_steps:
            self.reporter_sink.stdout(f"Phase: {phase_desc.phase_name}")
            for step_name in phase_desc.step_names:
                self.reporter_sink.stdout(f"  Step: {step_name}")
        if len(execution_description.matrix_description) > 0:
            self.reporter_sink.stdout("Matrix Description")
            for line in execution_description.matrix_description:
                self.reporter_sink.stdout(f"  {line}")

    def report_pre_execution_report(self, report: Report) -> None:
        self.reporter_sink.stdout("[Pre-Execution Report]")
        self.reporter_sink.increase_indentation()
        repo_to_reporter_sink(report, self.reporter_sink)
        self.reporter_sink.decrease_indentation()

    def report_validation_report(self, report: OrchestratorExecutorVisitReports) -> None:
        self.reporter_sink.stdout("[Validation Report]")

        for phase_report in report:
            self.reporter_sink.increase_indentation()
            for step_report in phase_report:
                self.reporter_sink.increase_indentation()
                repo_to_reporter_sink(step_report, self.reporter_sink)
                self.reporter_sink.decrease_indentation()
            self.reporter_sink.decrease_indentation()

    def report_skip_execution(self, exec_desc: str) -> None:
        self.reporter_sink.stdout(f"[Skip Execution {exec_desc}]")

    def report_start_execution(self, exec_desc: str) -> None:
        self.reporter_sink.reset_indentation()
        self.reporter_sink.stdout(f"[Start Execution {exec_desc}]")
        self.reporter_sink.increase_indentation()

    def report_execution_report(self, report_visit: OrchestratorExecutorVisitReports) -> None:
        self.reporter_sink.stdout("[Execution Report]")
        self.reporter_sink.increase_indentation()
        for phase_report in report_visit:
            self.reporter_sink.increase_indentation()
            for step_report in phase_report:
                self.reporter_sink.increase_indentation()
                repo_to_reporter_sink(step_report, self.reporter_sink)
                self.reporter_sink.decrease_indentation()
            self.reporter_sink.decrease_indentation()
        self.reporter_sink.decrease_indentation()
        self.reporter_sink.decrease_indentation()  # decrease the report_start_execution
