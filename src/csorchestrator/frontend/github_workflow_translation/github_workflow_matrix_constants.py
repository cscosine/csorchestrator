from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    create_context_os_architecture_compiler_generator_string_from_components,
    create_header_only_variant_string_from_components,
)


class MatrixOsArchCompilerGeneratorGithubConstants:
    # not embraced
    MATRIX_OS_NAME: str = "matrix.os"
    MATRIX_OS_VERSION: str = "matrix.os_version"
    MATRIX_ARCHITECTURE: str = "matrix.architecture"

    # embraced
    MATRIX_EXECUTION_ID_EMBRACED: str = "${{ matrix.execution_id }}"
    MATRIX_RUNS_ON_RUNNER_NAME_EMBRACED: str = "${{ matrix.runner }}"
    MATRIX_OS_NAME_EMBRACED: str = "${{ matrix.os }}"
    MATRIX_OS_VERSION_EMBRACED: str = "${{ matrix.os_version }}"
    MATRIX_ARCHITECTURE_EMBRACED: str = "${{ matrix.architecture }}"
    MATRIX_ARCHITECTURE_VARIANT_EMBRACED: str = "${{ matrix.architecture_variant }}"
    MATRIX_COMPILER_EMBRACED: str = "${{ matrix.compiler }}"
    MATRIX_COMPILER_VERSION_EMBRACED: str = "${{ matrix.compiler_version }}"
    MATRIX_GENERATOR_EMBRACED: str = "${{ matrix.generator }}"
    MATRIX_GENERATOR_TYPE_EMBRACED: str = "${{ matrix.generator_type }}"
    MATRIX_GENERATOR_CMAKE_EMBRACED: str = "${{ matrix.generator_cmake }}"
    C_COMPILER_EMBRACED: str = "${{ matrix.c_compiler }}"
    CPP_COMPILER_EMBRACED: str = "${{ matrix.cpp_compiler }}"
    TOOLSET_EMBRACED: str = "${{ matrix.toolset }}"


def create_header_only_variant_string_github_matrix() -> str:
    return create_header_only_variant_string_from_components(
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_NAME_EMBRACED
    )


def create_context_os_architecture_compiler_generator_string_github_matrix() -> str:
    return create_context_os_architecture_compiler_generator_string_from_components(
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_NAME_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_VERSION_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_VARIANT_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_VERSION_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_EMBRACED,
    )
