from dataclasses import dataclass
from enum import Enum
from typing import assert_never

from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    GeneratorType,
    GeneratorWithType,
)
from csorchestrator.domain.context.context_os_architecture import (
    ARCHITECTURE_VARIANT_GENERIC,
    OS,
    Architecture,
    ContextOsArchitecture,
    UbuntuVersions,
    WindowsVersions,
)
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
    create_context_os_architecture_compiler_generator_string_from_components,
)
from csorchestrator.frontend.github_workflow_translation.github_workflow_matrix_constants import (
    MatrixOsArchCompilerGeneratorGithubConstants,
)

# TODO this is a glue layer between csorchestrator and cscmake
# it should not strictly belong to csorchestrator, but having it in cscmake
# at the moment is complicated: cscmake is normally cloned by project
# therefore it is not available in imports until it is cloned...
# so, for the time being, this can stay here
# once cscmake will be stable and usable via pip install, then we can move this file there


def get_supported_os_version_list(os: OS) -> list[str]:
    match os:
        case OS.LINUX:
            return [UbuntuVersions.UBUNTU_22_04.value, UbuntuVersions.UBUNTU_24_04.value]
        case OS.WINDOWS:
            return [WindowsVersions.WIN10.value]
        case OS.MACOS:
            return []  # TODO add MACOS support
        case _:
            assert_never(os)


class BuildConfig(Enum):
    DEBUG = "debug"
    RELEASE = "release"
    PARANOID = "paranoid"
    RELWITHDEBINFO = "relWithDebInfo"
    DEBUG_RELEASE = "debug-release"
    DEBUG_RELEASE_RELWITHDEBINFO_PARANOID = "debug-release-relWithDebInfo-paranoid"


def get_supported_build_configs_for_generator_type(
    generator_type: GeneratorType,
) -> list[BuildConfig]:
    match generator_type:
        case GeneratorType.SINGLE_CONFIG:
            return [
                BuildConfig.DEBUG,
                BuildConfig.RELEASE,
                BuildConfig.RELWITHDEBINFO,
                BuildConfig.PARANOID,
            ]
        case GeneratorType.MULTI_CONFIG:
            return [
                BuildConfig.DEBUG,
                BuildConfig.RELEASE,
                BuildConfig.RELWITHDEBINFO,
                BuildConfig.PARANOID,
                BuildConfig.DEBUG_RELEASE,
                BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
            ]
        case _:
            assert_never(generator_type)


def get_default_generators_linux(arch: Architecture) -> list[GeneratorWithType]:
    lst: list[GeneratorWithType] = []
    match arch:
        case Architecture.X64:
            lst += [GeneratorWithType.NINJA_MULTI]
        case Architecture.ARM64:
            lst += [GeneratorWithType.NINJA]
        case _:
            assert_never(arch)
    return lst


def get_default_generators_windows() -> list[GeneratorWithType]:
    return [
        GeneratorWithType.MSVC_17_2022,
        GeneratorWithType.MSVC_18_2026,
    ]


def get_supported_compilers_linux() -> list[Compiler]:
    return [Compiler.GCC, Compiler.CLANG]


def get_supported_compilers_windows() -> list[tuple[Compiler, str]]:
    return [
        (Compiler.MSVC, ContextCompilerGenerator.COMPILER_VERSION_DEFAULT),
        (Compiler.MSVC_CLANG, ContextCompilerGenerator.COMPILER_VERSION_DEFAULT),
    ]


def get_supported_compilers_windows_ninja_generator() -> list[tuple[Compiler, str]]:
    return [
        (Compiler.MSVC, ContextCompilerGenerator.COMPILER_VERSION_MSVC_2022_17),
        (Compiler.MSVC_CLANG, ContextCompilerGenerator.COMPILER_VERSION_MSVC_2022_17),
        (Compiler.MSVC, ContextCompilerGenerator.COMPILER_VERSION_MSVC_2026_18),
        (Compiler.MSVC_CLANG, ContextCompilerGenerator.COMPILER_VERSION_MSVC_2026_18),
    ]


def get_supported_context_os_architecture_list() -> list[ContextOsArchitectureCompilerGenerator]:

    ret_list: list[ContextOsArchitectureCompilerGenerator] = []

    ## LINUX. use multi-config for x64 arch, use single config for arm64 arch
    for os_version in get_supported_os_version_list(OS.LINUX):
        for arch in [Architecture.X64, Architecture.ARM64]:
            os_arch = ContextOsArchitecture(
                os=OS.LINUX,
                os_version=os_version,
                architecture=arch,
                architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
            )
            generators = get_default_generators_linux(arch)
            compilers = get_supported_compilers_linux()

            for compiler in compilers:
                for generator in generators:
                    ccg = ContextCompilerGenerator(
                        compiler_family=compiler,
                        compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
                        build_generator=generator,
                    )
                    ret_list.append(
                        ContextOsArchitectureCompilerGenerator(
                            context_os_architecture=os_arch, context_compiler_generator=ccg
                        )
                    )

    ## WINDOWS
    for os_version in get_supported_os_version_list(OS.WINDOWS):
        os_arch = ContextOsArchitecture(
            os=OS.WINDOWS,
            os_version=os_version,
            architecture=Architecture.X64,
            architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
        )

        generators = get_default_generators_windows()
        compilers_and_version = get_supported_compilers_windows()

        for compiler, version in compilers_and_version:
            for generator in generators:
                ccg = ContextCompilerGenerator(
                    compiler_family=compiler,
                    compiler_version=version,
                    build_generator=generator,
                )
                ret_list.append(
                    ContextOsArchitectureCompilerGenerator(
                        context_os_architecture=os_arch, context_compiler_generator=ccg
                    )
                )
    ## MACOS
    # for os_version in get_supported_os_version_list(OS.MACOS):
    #     _ = os_version  # TODO add MACOS support

    return ret_list


@dataclass
class ContextOsArchitectureCompilerGeneratorConfig(ContextOsArchitectureCompilerGenerator):
    config: BuildConfig


def get_supported_context_os_architecture_config(
    src: ContextOsArchitectureCompilerGenerator,
) -> list[ContextOsArchitectureCompilerGeneratorConfig]:

    ret_list: list[ContextOsArchitectureCompilerGeneratorConfig] = []

    configs_per_generator_type = get_supported_build_configs_for_generator_type(
        src.context_compiler_generator.build_generator.generator_type
    )
    for config in configs_per_generator_type:
        ret_list.append(
            ContextOsArchitectureCompilerGeneratorConfig(
                context_os_architecture=src.context_os_architecture,
                context_compiler_generator=src.context_compiler_generator,
                config=config,
            )
        )

    return ret_list


def is_config_selected_multi_config_generator(current_config: BuildConfig, requested_config: BuildConfig) -> bool:
    # verbose but defensive, if used without type checks in place
    if (
        requested_config == BuildConfig.DEBUG
        or requested_config == BuildConfig.RELEASE
        or requested_config == BuildConfig.RELWITHDEBINFO
        or requested_config == BuildConfig.PARANOID
        or requested_config == BuildConfig.DEBUG_RELEASE
        or requested_config == BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID
    ):
        return requested_config == current_config
    else:
        return False


def is_config_selected_single_config_generator(current_config: BuildConfig, requested_config: BuildConfig) -> bool:
    if (
        requested_config == BuildConfig.DEBUG
        or requested_config == BuildConfig.RELEASE
        or requested_config == BuildConfig.RELWITHDEBINFO
        or requested_config == BuildConfig.PARANOID
    ) and current_config == requested_config:
        return True
    elif requested_config == BuildConfig.DEBUG_RELEASE:
        if current_config == BuildConfig.DEBUG or current_config == BuildConfig.RELEASE:
            return True
    elif requested_config == BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID and (
        current_config == BuildConfig.DEBUG
        or current_config == BuildConfig.RELEASE
        or current_config == BuildConfig.RELWITHDEBINFO
        or current_config == BuildConfig.PARANOID
    ):
        return True
    return False


def is_config_selected_for_generator(
    generator_type: GeneratorType,
    current_config: BuildConfig,
    requested_config: BuildConfig,
) -> bool:
    match generator_type:
        case GeneratorType.SINGLE_CONFIG:
            return is_config_selected_single_config_generator(
                current_config=current_config, requested_config=requested_config
            )
        case GeneratorType.MULTI_CONFIG:
            return is_config_selected_multi_config_generator(
                current_config=current_config, requested_config=requested_config
            )
        case _:
            assert_never(generator_type)


def workflow_name_from_description(
    description: ContextOsArchitectureCompilerGeneratorConfig,
) -> str:
    supported_build_config_string = create_context_os_architecture_compiler_generator_string(description)

    config_string = description.config.value
    workflow_name = f"workflow-{supported_build_config_string}-{config_string}"
    return workflow_name


def workflow_name_from_matrix_components(config_string: str) -> str:
    return workflow_name_from_components(
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_NAME_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_OS_VERSION_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_ARCHITECTURE_VARIANT_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_COMPILER_VERSION_EMBRACED,
        MatrixOsArchCompilerGeneratorGithubConstants.MATRIX_GENERATOR_EMBRACED,
        config_string,
    )


def workflow_name_from_components(
    os: str,
    os_version: str,
    architecture: str,
    architecture_variant: str,
    compiler: str,
    compiler_version: str,
    build_generator: str,
    config_string: str,
) -> str:

    supported_build_config_string = create_context_os_architecture_compiler_generator_string_from_components(
        os, os_version, architecture, architecture_variant, compiler, compiler_version, build_generator
    )

    workflow_name = f"workflow-{supported_build_config_string}-{config_string}"
    return workflow_name


def get_all_supported_workflow_descriptions(
    selected_config: BuildConfig,
    os_arch_generator: ContextOsArchitectureCompilerGenerator,
) -> list[ContextOsArchitectureCompilerGeneratorConfig]:
    workflow_list: list[ContextOsArchitectureCompilerGeneratorConfig] = []

    for supported_build_config in get_supported_context_os_architecture_config(os_arch_generator):
        if not is_config_selected_for_generator(
            supported_build_config.context_compiler_generator.build_generator.generator_type,
            supported_build_config.config,
            selected_config,
        ):
            continue
        workflow_list.append(supported_build_config)

    return workflow_list
