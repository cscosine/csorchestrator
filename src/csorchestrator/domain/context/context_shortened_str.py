from csorchestrator.domain.context.context_compiler_generator import Compiler, ContextCompilerGenerator, Generator
from csorchestrator.domain.context.context_os_architecture import (
    ARCHITECTURE_VARIANT_ARM64_NANO,
    ARCHITECTURE_VARIANT_ARM64_ORIN,
    ARCHITECTURE_VARIANT_ARM64_XAVIER,
    ARCHITECTURE_VARIANT_GENERIC,
    OS,
    UBUNTU_STRING_PREFIX,
    Architecture,
)

CSORCHESTRATOR_SCHEMA_VERSION_SHORT = "v1"


def short_os_name(os: OS) -> str:
    # TODO add a test that this stays unique
    return f"{os.value[0]}"


def short_os_version(os: OS, version: str) -> str:
    if os == OS.LINUX:
        return version.replace(UBUNTU_STRING_PREFIX, UBUNTU_STRING_PREFIX[0])
    elif os == OS.WINDOWS:
        return version  # short enough
    elif os == OS.MACOS:
        return version  # TODO shorten mac version if needed
    else:
        return version  # fallback is not shortened


def short_architecture(arch: Architecture) -> str:
    if arch == Architecture.X64:
        return str(arch.value)
    elif arch == Architecture.ARM64:
        return "a64"
    else:  # fallback
        return arch.value


def short_architecture_variant(arch: Architecture, variant: str) -> str:
    if variant == ARCHITECTURE_VARIANT_GENERIC:
        return "g"
    elif variant == ARCHITECTURE_VARIANT_ARM64_ORIN:
        return "o"
    elif variant == ARCHITECTURE_VARIANT_ARM64_XAVIER:
        return "x"
    elif variant == ARCHITECTURE_VARIANT_ARM64_NANO:
        return "n"
    else:
        return variant  # fallback not shortened


def short_generator(g: Generator) -> str:
    if g == Generator.NINJA:
        return "n"
    elif g == Generator.NINJA_MULTI:
        return "nm"
    elif g == Generator.MSVC_17_2022:
        return "ms22"
    elif g == Generator.MSVC_18_2026:
        return "ms26"
    else:
        return g.value


def short_compiler_family(c: Compiler) -> str:
    if c == Compiler.MSVC:
        return "m"
    elif c == Compiler.MSVC_CLANG:
        return "mc"
    elif c == Compiler.CLANG:
        return "c"
    elif c == Compiler.GCC:
        return "g"
    elif c == Compiler.APPLE_CLANG:
        return "ac"
    else:
        return c.value


def short_compiler_version(c: Compiler, v: str) -> str:
    if v == ContextCompilerGenerator.COMPILER_VERSION_DEFAULT:
        return "d"
    else:
        return v
