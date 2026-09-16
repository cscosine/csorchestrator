from dataclasses import dataclass

from csorchestrator.domain.orchestrator.orchestrator import MatrixExecutionBase, Orchestrator
from csorchestrator.domain.orchestrator.phase import Phase
from csorchestrator.domain.orchestrator.step_base import StepBase


@dataclass
class StepEchoMessage(StepBase):
    message: str


def test_orchestrator_add_phases() -> None:
    o = Orchestrator("myName", "0.0.0", MatrixExecutionBase("exec-job"))

    p = Phase("phase_1").add_step(StepEchoMessage(name="p1s1", description="p1 step s1", message="phase 1 step 2"))
    p.add_step(StepEchoMessage(name="p1s2", description="p1 step s2", message="phase 1 step 2"))
    pb = Phase("phase_1b").add_step(StepEchoMessage(name="p1bs1", description="p1b step s1", message="phase 1b step 2"))

    o.add_phase(p).add_phase(pb)

    o.create_phase("phase_2").add_step(
        StepEchoMessage(name="p2s1", description="p2 step s1", message="phase 2 step 1")
    ).add_step(StepEchoMessage(name="p2s2", description="p2 step s2", message="phase 2 step 2")).add_step(
        StepEchoMessage(name="p2s2", description="p2 step s2", message="phase 2 step 3")
    )

    assert len(o.phases) == 3
    assert len(o.phases[0].steps) == 2
    assert len(o.phases[1].steps) == 1
    assert len(o.phases[2].steps) == 3


# ------------------------------------------------------------------------------------------------


def test_orchestrator_executor_minimal_description() -> None:
    o = Orchestrator("myName", "0.0.0", MatrixExecutionBase("exec-job"))

    o.create_phase("p1").add_step(StepEchoMessage(name="p1s1", description="p1 step s1", message="")).add_step(
        StepEchoMessage(name="p1s2", description="p1 step s2", message="")
    ).add_step(StepEchoMessage(name="p1s3", description="p1 step s3", message=""))

    o.create_phase("p2").add_step(StepEchoMessage(name="p2s1", description="p2 step s1", message="")).add_step(
        StepEchoMessage(name="p2s2", description="p2 step s2", message="")
    )

    min_desc = o.extract_minimal_description()
    od = min_desc.phases_and_steps

    assert len(od) == 2

    # phases
    assert od[0].phase_name == "p1"
    assert od[1].phase_name == "p2"

    # steps
    assert len(od[0].step_names) == 3
    assert od[0].step_names[0] == "p1s1"
    assert od[0].step_names[1] == "p1s2"
    assert od[0].step_names[2] == "p1s3"

    assert len(od[1].step_names) == 2
    assert od[1].step_names[0] == "p2s1"
    assert od[1].step_names[1] == "p2s2"


# ------------------------------------------------------------------------------------------------


def _orchestrator_with_one_phase(name: str = "phase_1") -> Orchestrator:
    o = Orchestrator("sub", "0.0.0", MatrixExecutionBase("exec-job"))
    o.create_phase(name).add_step(StepEchoMessage(name="s1", description="s1", message="")).add_step(
        StepEchoMessage(name="s2", description="s2", message="")
    )
    return o


def test_orchestrator_append_merges_phases() -> None:
    o = Orchestrator("main", "0.0.0", MatrixExecutionBase("exec-job"))
    o.create_phase("main_phase")

    other = _orchestrator_with_one_phase()
    o.append(other)

    assert len(o.phases) == 2
    assert [p.name for p in o.phases] == ["main_phase", "phase_1"]
    # the source orchestrator is left untouched
    assert len(other.phases) == 1


def test_orchestrator_append_with_prefix_namespaces_phase_and_step_names() -> None:
    o = Orchestrator("main", "0.0.0", MatrixExecutionBase("exec-job"))
    # same phase/step names as the appended sub-orchestrator: without a
    # prefix the appended names would clash at validation time.
    o.create_phase("phase_1").add_step(StepEchoMessage(name="s1", description="s1", message=""))

    o.append(_orchestrator_with_one_phase(), prefix="3rdparty: ")

    assert [p.name for p in o.phases] == ["phase_1", "3rdparty: phase_1"]
    appended = o.phases[1]
    assert [s.name for s in appended.steps] == ["3rdparty: s1", "3rdparty: s2"]


def test_orchestrator_append_reuses_source_with_different_prefixes() -> None:
    o = Orchestrator("main", "0.0.0", MatrixExecutionBase("exec-job"))
    other = _orchestrator_with_one_phase()

    o.append(other, prefix="a: ")
    o.append(other, prefix="b: ")

    assert [p.name for p in o.phases] == ["a: phase_1", "b: phase_1"]
    assert len(other.phases) == 1
