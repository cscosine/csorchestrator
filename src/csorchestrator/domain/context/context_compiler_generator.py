from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class Compiler(Enum):
    MSVC = "msvc"
    MSVC_CLANG = "msvcclang"
    CLANG = "clang"
    GCC = "gcc"
    APPLE_CLANG = "appleclang"

    def get_c_cpp_compiler(self) -> tuple[str | None, str | None]:
        if self == Compiler.GCC:
            return ("gcc", "g++")
        elif self == Compiler.CLANG:
            return ("clang", "clang++")
        if self == Compiler.APPLE_CLANG:
            return ("clang", "clang++")
        else:
            return (None, None)

    def get_cmake_toolset(self) -> str | None:
        if self == Compiler.MSVC_CLANG:
            return "ClangCL"
        return None


class Generator(Enum):
    NINJA = "ninja"
    NINJA_MULTI = "ninjamulticonfig"
    MSVC_17_2022 = "msvc2022"
    MSVC_18_2026 = "msvc2026"
    XCODE = "xcode"

    def get_cmake_generator_name(self) -> str | None:
        if self == Generator.NINJA:
            return "Ninja"
        elif self == Generator.NINJA_MULTI:
            return "Ninja Multi-Config"
        elif self == Generator.MSVC_17_2022:
            return "Visual Studio 17 2022"
        elif self == Generator.MSVC_18_2026:
            return "Visual Studio 18 2026"
        elif self == Generator.XCODE:
            return "Xcode"
        else:
            return None


class GeneratorType(Enum):
    SINGLE_CONFIG = "singleconfig"
    MULTI_CONFIG = "multiconfig"


@dataclass(frozen=True)
class GeneratorWithType:
    generator: Generator
    generator_type: GeneratorType

    # class vars (declared for typing only)
    NINJA: ClassVar["GeneratorWithType"]
    NINJA_MULTI: ClassVar["GeneratorWithType"]
    MSVC_17_2022: ClassVar["GeneratorWithType"]
    MSVC_18_2026: ClassVar["GeneratorWithType"]
    XCODE: ClassVar["GeneratorWithType"]


# define them AFTER the class exists
GeneratorWithType.NINJA = GeneratorWithType(
    Generator.NINJA,
    GeneratorType.SINGLE_CONFIG,
)

GeneratorWithType.NINJA_MULTI = GeneratorWithType(
    Generator.NINJA_MULTI,
    GeneratorType.MULTI_CONFIG,
)

GeneratorWithType.MSVC_17_2022 = GeneratorWithType(
    Generator.MSVC_17_2022,
    GeneratorType.MULTI_CONFIG,
)

GeneratorWithType.MSVC_18_2026 = GeneratorWithType(
    Generator.MSVC_18_2026,
    GeneratorType.MULTI_CONFIG,
)

GeneratorWithType.XCODE = GeneratorWithType(
    Generator.XCODE,
    GeneratorType.MULTI_CONFIG,
)


@dataclass(frozen=True)
class ContextCompilerGenerator:
    compiler_family: Compiler
    compiler_version: str  # string, use "default" for os/generator default compiler

    build_generator: GeneratorWithType

    COMPILER_VERSION_DEFAULT: str = "default"

    COMPILER_VERSION_MSVC_2026_18: str = "MSVC_2026_18"
    COMPILER_VERSION_MSVC_2022_17: str = "MSVC_2022_17"
