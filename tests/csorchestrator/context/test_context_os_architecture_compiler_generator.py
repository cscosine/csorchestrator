from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    Generator,
    GeneratorType,
    GeneratorWithType,
)
from csorchestrator.domain.context.context_os_architecture import (
    ARCHITECTURE_VARIANT_ARM64_ORIN,
    ARCHITECTURE_VARIANT_GENERIC,
    OS,
    Architecture,
    ContextOsArchitecture,
    UbuntuVersions,
    WindowsVersions,
)
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    CSORCHESTRATOR_SCHEMA_VERSION,
    ContextOsArchitectureCompilerGenerator,
    create_context_os_architecture_compiler_generator_string,
)


def test_basic_linux_ninja_clang():
    context_os = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )

    context_compiler = ContextCompilerGenerator(
        compiler_family=Compiler.CLANG,
        compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
        build_generator=GeneratorWithType(Generator.NINJA, GeneratorType.SINGLE_CONFIG),
    )

    result = create_context_os_architecture_compiler_generator_string(
        ContextOsArchitectureCompilerGenerator(context_os, context_compiler)
    )

    assert result == "-".join(
        [
            CSORCHESTRATOR_SCHEMA_VERSION,
            OS.LINUX.value,
            UbuntuVersions.UBUNTU_24_04.value,
            Architecture.ARM64.value,
            ARCHITECTURE_VARIANT_ARM64_ORIN,
            Compiler.CLANG.value,
            ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            Generator.NINJA.value,
        ]
    )


def test_windows_msvc_vs_generator():
    context_os = ContextOsArchitecture(
        os=OS.WINDOWS,
        os_version=WindowsVersions.WIN10.value,
        architecture=Architecture.X64,
        architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
    )

    context_compiler = ContextCompilerGenerator(
        compiler_family=Compiler.MSVC,
        compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
        build_generator=GeneratorWithType(Generator.MSVC_17_2022, GeneratorType.MULTI_CONFIG),
    )

    result = create_context_os_architecture_compiler_generator_string(
        ContextOsArchitectureCompilerGenerator(context_os, context_compiler)
    )

    assert result == "-".join(
        [
            CSORCHESTRATOR_SCHEMA_VERSION,
            OS.WINDOWS.value,
            WindowsVersions.WIN10.value,
            Architecture.X64.value,
            ARCHITECTURE_VARIANT_GENERIC,
            Compiler.MSVC.value,
            ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            Generator.MSVC_17_2022.value,
        ]
    )


def test_macos_appleclang_ninja_multiconfig():
    context_os = ContextOsArchitecture(
        os=OS.MACOS,
        os_version="v14",
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
    )

    context_compiler = ContextCompilerGenerator(
        compiler_family=Compiler.APPLE_CLANG,
        compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
        build_generator=GeneratorWithType(Generator.NINJA_MULTI, GeneratorType.MULTI_CONFIG),
    )

    result = create_context_os_architecture_compiler_generator_string(
        ContextOsArchitectureCompilerGenerator(context_os, context_compiler)
    )

    assert result == "-".join(
        [
            CSORCHESTRATOR_SCHEMA_VERSION,
            OS.MACOS.value,
            "v14",
            Architecture.ARM64.value,
            ARCHITECTURE_VARIANT_GENERIC,
            Compiler.APPLE_CLANG.value,
            ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            Generator.NINJA_MULTI.value,
        ]
    )


def test_lowercasing_behavior():
    context_os = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN.upper(),
    )
    # test that uppercasing does not affect the result

    context_compiler = ContextCompilerGenerator(
        compiler_family=Compiler.CLANG,
        compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
        build_generator=GeneratorWithType(Generator.NINJA, GeneratorType.SINGLE_CONFIG),
    )

    result = create_context_os_architecture_compiler_generator_string(
        ContextOsArchitectureCompilerGenerator(context_os, context_compiler)
    )

    assert result == "-".join(
        [
            CSORCHESTRATOR_SCHEMA_VERSION,
            OS.LINUX.value,
            UbuntuVersions.UBUNTU_24_04.value,
            Architecture.ARM64.value,
            ARCHITECTURE_VARIANT_ARM64_ORIN,
            Compiler.CLANG.value,
            ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            Generator.NINJA.value,
        ]
    )


def test_all_generators_supported():
    base_os = ContextOsArchitecture(
        os=OS.LINUX,
        os_version="5.0",
        architecture=Architecture.X64,
        architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
    )

    for gen, expected in [
        (GeneratorWithType(Generator.NINJA, GeneratorType.SINGLE_CONFIG), Generator.NINJA.value),
        (GeneratorWithType(Generator.NINJA_MULTI, GeneratorType.MULTI_CONFIG), Generator.NINJA_MULTI.value),
        (GeneratorWithType(Generator.MSVC_17_2022, GeneratorType.MULTI_CONFIG), Generator.MSVC_17_2022.value),
        (GeneratorWithType(Generator.MSVC_18_2026, GeneratorType.MULTI_CONFIG), Generator.MSVC_18_2026.value),
    ]:
        context_compiler = ContextCompilerGenerator(
            compiler_family=Compiler.GCC,
            compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            build_generator=gen,
        )

        result = create_context_os_architecture_compiler_generator_string(
            ContextOsArchitectureCompilerGenerator(base_os, context_compiler)
        )

        assert expected in result
