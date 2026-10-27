from unittest.mock import patch

from csorchestrator.domain.context.context_os_architecture import (
    ARCHITECTURE_VARIANT_ARM64_ORIN,
    ARCHITECTURE_VARIANT_ARM64_XAVIER,
    ARCHITECTURE_VARIANT_GENERIC,
    OS,
    Architecture,
    ContextOsArchitecture,
    UbuntuVersions,
    detect_context_os_architecture,
)
from csorchestrator.foundation.core.expected import Expected

# =========================================================
# SUCCESS
# =========================================================


def test_detect_context_os_architecture_success():
    with (
        patch(
            "csorchestrator.domain.context.context_os_architecture.detect_os",
            return_value=Expected.make_value(
                (
                    OS.LINUX,
                    UbuntuVersions.UBUNTU_24_04.value,
                )
            ),
        ),
        patch(
            "csorchestrator.domain.context.context_os_architecture.detect_architecture",
            return_value=Expected.make_value(
                (
                    Architecture.ARM64,
                    ARCHITECTURE_VARIANT_ARM64_ORIN,
                )
            ),
        ),
    ):
        result = detect_context_os_architecture()

    assert result.error is None

    assert result.value == ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )


# =========================================================
# OS ERROR
# =========================================================


def test_detect_context_os_architecture_os_error():
    with patch(
        "csorchestrator.domain.context.context_os_architecture.detect_os",
        return_value=Expected.make_error("Unsupported OS"),
    ):
        result = detect_context_os_architecture()

    assert result.value is None
    assert result.error == "Unsupported OS"


# =========================================================
# ARCHITECTURE ERROR
# =========================================================


def test_detect_context_os_architecture_architecture_error():
    with (
        patch(
            "csorchestrator.domain.context.context_os_architecture.detect_os",
            return_value=Expected.make_value(
                (
                    OS.LINUX,
                    UbuntuVersions.UBUNTU_24_04,
                )
            ),
        ),
        patch(
            "csorchestrator.domain.context.context_os_architecture.detect_architecture",
            return_value=Expected.make_error("Unsupported architecture"),
        ),
    ):
        result = detect_context_os_architecture()

    assert result.value is None
    assert result.error == "Unsupported architecture"


# test can be executed on
def test_context_os_architecture_can_be_executed_on():
    a1 = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )
    a2 = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )
    a3 = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_XAVIER,
    )

    assert a1.can_be_executed_on(a2)
    assert not a1.can_be_executed_on(a3)


# test can be executed on - orin special case
def test_context_os_architecture_can_be_executed_on_orin():
    host = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )
    entry = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
    )
    hostx64 = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_24_04.value,
        architecture=Architecture.X64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )
    host2204 = ContextOsArchitecture(
        os=OS.LINUX,
        os_version=UbuntuVersions.UBUNTU_22_04.value,
        architecture=Architecture.ARM64,
        architecture_variant=ARCHITECTURE_VARIANT_ARM64_ORIN,
    )

    assert entry.can_be_executed_on(host)
    assert not entry.can_be_executed_on(hostx64)
    assert not entry.can_be_executed_on(host2204)
