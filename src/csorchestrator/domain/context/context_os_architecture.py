import platform
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from csorchestrator.foundation.core.expected import Expected


class OS(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


OS_PLATFORM_MACOS: str = "darwin"

VERSION_STRING_PREFIX = "v"


class WindowsVersions(Enum):
    WIN10 = "v10"


UBUNTU_STRING_PREFIX = "ubuntu"


class UbuntuVersions(Enum):
    UBUNTU_22_04 = UBUNTU_STRING_PREFIX + "22.04"
    UBUNTU_24_04 = UBUNTU_STRING_PREFIX + "24.04"


class Architecture(Enum):
    X64 = "x64"
    ARM64 = "arm64"


class MachineArchitecture(Enum):
    AMD64 = "amd64"
    X86_64 = "x86_64"
    X64 = "x64"
    AARCH64 = "aarch64"
    ARM64 = "arm64"


ARCHITECTURE_VARIANT_GENERIC: str = "generic"
ARCHITECTURE_VARIANT_ARM64_ORIN: str = "orin"
ARCHITECTURE_VARIANT_ARM64_XAVIER: str = "xavier"
ARCHITECTURE_VARIANT_ARM64_NANO: str = "nano"


@dataclass(frozen=True)
class ContextOsArchitecture:
    os: OS
    os_version: str

    architecture: Architecture
    architecture_variant: str  # GENERIC ORIN XAVIER NANO

    def can_be_executed_on(self, other: "ContextOsArchitecture") -> bool:
        if self.os == OS.WINDOWS and other.os == OS.WINDOWS:
            # do not check version
            return (
                self.os == other.os
                and self.architecture == other.architecture
                and self.architecture_variant == other.architecture_variant
            )
        else:
            return (
                self.os == other.os
                and self.os_version == other.os_version
                and self.architecture == other.architecture
                and self.architecture_variant == other.architecture_variant
            )


# =========================================================
# OS / ARCH DETECTION
# =========================================================


# return the os name if not supported in the expected
def detect_os() -> Expected[tuple[OS, str], str]:

    system = platform.system().lower()

    # -----------------------------------------------------
    # WINDOWS
    # -----------------------------------------------------

    if system == OS.WINDOWS.value:
        version = platform.release()

        return Expected[tuple[OS, str], str].make_value((OS.WINDOWS, VERSION_STRING_PREFIX + version))

    # -----------------------------------------------------
    # LINUX
    # -----------------------------------------------------

    if system == "linux":
        os_release = Path("/etc/os-release")

        if os_release.exists():
            content = os_release.read_text()

            distro_match = re.search(r'^ID="?([^"\n]+)"?', content, re.MULTILINE)
            version_match = re.search(r'^VERSION_ID="?([^"\n]+)"?', content, re.MULTILINE)

            if distro_match and version_match:
                distro = distro_match.group(1).lower() + version_match.group(1).lower()
                return Expected[tuple[OS, str], str].make_value((OS.LINUX, distro))
            else:
                return Expected[tuple[OS, str], str].make_error(f"Unsupported linux with /etc/os-release: {content}")

    if system == OS_PLATFORM_MACOS:
        version = platform.mac_ver()[0]
        return Expected[tuple[OS, str], str].make_value((OS.MACOS, VERSION_STRING_PREFIX + version))

    return Expected[tuple[OS, str], str].make_error(f"Unsupported OS: {system}")


def detect_architecture() -> Expected[tuple[Architecture, str], str]:

    machine = platform.machine().lower()

    # -----------------------------------------------------
    # X64
    # -----------------------------------------------------

    if machine in [MachineArchitecture.AMD64.value, MachineArchitecture.X86_64.value, MachineArchitecture.X64.value]:
        return Expected[tuple[Architecture, str], str].make_value((Architecture.X64, ARCHITECTURE_VARIANT_GENERIC))

    # -----------------------------------------------------
    # ARM64
    # -----------------------------------------------------

    if machine in [MachineArchitecture.AARCH64.value, MachineArchitecture.ARM64.value]:
        variant = detect_arm64_variant()

        return Expected[tuple[Architecture, str], str].make_value((Architecture.ARM64, variant))

    return Expected[tuple[Architecture, str], str].make_error(f"Unsupported architecture: {machine}")


def detect_arm64_variant() -> str:

    # -----------------------------------------------------
    # NVIDIA JETSON DETECTION
    # -----------------------------------------------------

    model_file = Path("/proc/device-tree/model")

    if model_file.exists():
        try:
            model = model_file.read_text().lower()

            if ARCHITECTURE_VARIANT_ARM64_ORIN in model:
                return ARCHITECTURE_VARIANT_ARM64_ORIN

            if ARCHITECTURE_VARIANT_ARM64_XAVIER in model:
                return ARCHITECTURE_VARIANT_ARM64_XAVIER

            if ARCHITECTURE_VARIANT_ARM64_NANO in model:
                return ARCHITECTURE_VARIANT_ARM64_NANO

        except Exception:
            pass

    return ARCHITECTURE_VARIANT_GENERIC


# =========================================================
# PUBLIC API
# =========================================================


def detect_context_os_architecture() -> Expected[ContextOsArchitecture, str]:

    os_result = detect_os()
    if os_result.error is not None:
        return Expected[ContextOsArchitecture, str].make_error(os_result.error)

    assert os_result.value is not None  # to make mypy happy need to check for None explicitly
    os_value, os_version = os_result.value

    arch_result = detect_architecture()
    if arch_result.error is not None:
        return Expected[ContextOsArchitecture, str].make_error(arch_result.error)

    assert arch_result.value is not None
    arch, arch_variant = arch_result.value

    return Expected[ContextOsArchitecture, str].make_value(
        ContextOsArchitecture(
            os=os_value,
            os_version=os_version,
            architecture=arch,
            architecture_variant=arch_variant,
        )
    )
