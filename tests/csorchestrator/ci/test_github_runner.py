import pytest

from csorchestrator.application.factory.factory import create_orchestrator_factory_all_supported_cases
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ExecutionMatrixOsArchCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
)
from csorchestrator.frontend.cscmake_presets.supported_variants import (
    get_context_list_linux,
    get_context_list_macos,
    get_supported_context_os_architecture_list,
)
from csorchestrator.frontend.github_workflow_translation.validate_and_generate_github_workflow import get_runner


@pytest.mark.parametrize(
    ("os_version", "expected"),
    [
        ("ubuntu22.04", ["ubuntu-22.04", "ubuntu-22.04", "ubuntu-22.04-arm", "ubuntu-22.04-arm"]),
        ("ubuntu24.04", ["ubuntu-24.04", "ubuntu-24.04", "ubuntu-24.04-arm", "ubuntu-24.04-arm"]),
        ("ubuntu26.04", ["ubuntu-26.04", "ubuntu-26.04", "ubuntu-26.04-arm", "ubuntu-26.04-arm"]),
    ],
)
def test_get_runner_linux(os_version: str, expected: list[str]) -> None:
    assert [get_runner(c).value for c in get_context_list_linux(os_version)] == expected


@pytest.mark.parametrize(("os_version", "expected"), [("macos15", "macos-15"), ("macos26", "macos-26")])
def test_get_runner_macos(os_version: str, expected: str) -> None:
    for c in get_context_list_macos(os_version):
        assert get_runner(c).value == expected


def test_get_runner_default_matrix() -> None:
    for c in get_supported_context_os_architecture_list():
        assert get_runner(c).error is None


def test_factory_additional_matrix_list() -> None:
    extra = get_context_list_linux("ubuntu26.04") + get_context_list_macos("macos15")
    o = create_orchestrator_factory_all_supported_cases(
        name="p",
        version="1.0.0",
        execution_matrix_name="m",
        additional_matrix_list=extra + get_context_list_linux("ubuntu22.04"),  # duplicates of the default ignored
    )
    assert isinstance(o.execution_matrix, ExecutionMatrixOsArchCompilerGenerator)
    ids = [
        create_context_os_architecture_compiler_generator_string(c)
        for c in o.execution_matrix.os_architecture_compiler_generator_list
    ]
    assert len(ids) == 12 + 6
    assert len(set(ids)) == len(ids)
    assert ids[12:] == [create_context_os_architecture_compiler_generator_string(c) for c in extra]
