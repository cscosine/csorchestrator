# =========================================================
# Workflow builder
# =========================================================
from dataclasses import dataclass, field
from typing import Any

from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    MatrixOsArchCompilerGeneratorGithubConstants,
)


@dataclass(frozen=True)
class MatrixOsArchCompilerGeneratorRunnerEntryInclude:
    original_os_architecture_compiler_generator_list: ContextOsArchitectureCompilerGenerator

    execution_id: str
    os: str
    os_version: str
    architecture: str
    architecture_variant: str
    compiler: str
    compiler_version: str
    build_generator: str
    build_generator_type: str
    generator_cmake: str
    runner: str
    c_compiler: str | None = None
    cpp_compiler: str | None = None
    toolset: str | None = None

    def to_dict(self) -> dict[str, Any]:
        ret = {
            "execution_id": self.execution_id,
            "os": self.os,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "architecture_variant": self.architecture_variant,
            "compiler": self.compiler,
            "compiler_version": self.compiler_version,
            "generator": self.build_generator,
            "generator_type": self.build_generator_type,
            "generator_cmake": self.generator_cmake,
            "runner": self.runner,
        }
        if self.c_compiler is not None:
            ret["c_compiler"] = self.c_compiler

        if self.cpp_compiler is not None:
            ret["cpp_compiler"] = self.cpp_compiler

        if self.toolset is not None:
            ret["toolset"] = self.toolset

        return ret


@dataclass
class JobStrategy:
    fail_fast: bool
    _matrix_includes: list[MatrixOsArchCompilerGeneratorRunnerEntryInclude] = field(default_factory=list)

    def add_matrix_include(self, entry: MatrixOsArchCompilerGeneratorRunnerEntryInclude) -> "JobStrategy":
        self._matrix_includes.append(entry)
        return self

    def to_dict(self) -> dict[str, Any]:
        ret: dict[str, Any] = {
            "fail-fast": self.fail_fast,
        }
        if len(self._matrix_includes) > 0:
            includes = []
            for matrix_include in self._matrix_includes:
                includes.append(matrix_include.to_dict())
            ret["matrix"] = {}
            ret["matrix"]["include"] = includes

        return ret


@dataclass
class JobOrchestratorMatrixExecution:
    name: str
    runs_on: str
    strategy: JobStrategy
    steps: list[GithubStepInterface] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            self.name: {
                "runs-on": self.runs_on,
                "strategy": self.strategy.to_dict(),
                "steps": [step.to_dict() for step in self.steps],
            }
        }


def create_job_from_matrix_list(
    name: str,
    matrix_list: list[MatrixOsArchCompilerGeneratorRunnerEntryInclude],
    fail_fast: bool,
) -> JobOrchestratorMatrixExecution:

    jd = JobOrchestratorMatrixExecution(
        name=name,
        runs_on=MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_RUNS_ON_RUNNER_NAME_EMBRACED,
        strategy=JobStrategy(fail_fast=fail_fast),
    )

    for matrix in matrix_list:
        jd.strategy.add_matrix_include(matrix)

    return jd
