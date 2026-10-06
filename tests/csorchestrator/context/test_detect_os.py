import platform
from unittest.mock import patch

import pytest

from csorchestrator.domain.context.context_os_architecture import (
    OS,
    OS_PLATFORM_MACOS,
    UBUNTU_STRING_PREFIX,
    VERSION_STRING_PREFIX,
    UbuntuVersions,
    WindowsVersions,
    detect_os,
)

# =========================================================
# WINDOWS
# =========================================================


@pytest.mark.skipif(platform.system().lower() != OS.WINDOWS.value, reason=OS.WINDOWS.value + "-only test")
def test_detect_os_real_windows():
    result = detect_os()

    assert result.error is None
    assert result.value is not None

    detected_os, version = result.value

    assert detected_os == OS.WINDOWS
    assert version[0] == VERSION_STRING_PREFIX


@pytest.mark.skipif(platform.system().lower() != OS.WINDOWS.value, reason=OS.WINDOWS.value + "-only test")
def test_detect_os_mock_linux_from_windows():
    os_release_content = f"""
ID={UBUNTU_STRING_PREFIX}
VERSION_ID="22.04"
"""

    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.release", return_value="6.8.0"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=os_release_content),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.LINUX, UbuntuVersions.UBUNTU_22_04.value)


@pytest.mark.skipif(platform.system().lower() != OS.WINDOWS.value, reason=OS.WINDOWS.value + "-only test")
def test_detect_os_mock_macos_from_windows():
    with (
        patch("platform.system", return_value="Darwin"),
        patch("platform.mac_ver", return_value=("14.5", ("", "", ""), "")),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.MACOS, "v14.5")


# =========================================================
# LINUX
# =========================================================


@pytest.mark.skipif(platform.system().lower() != OS.LINUX.value, reason=OS.LINUX.value + "-only test")
def test_detect_os_real_linux():
    result = detect_os()

    assert result.error is None
    assert result.value is not None

    detected_os, distro = result.value

    assert detected_os == OS.LINUX
    assert distro != ""


@pytest.mark.skipif(platform.system().lower() != OS.LINUX.value, reason=OS.LINUX.value + "-only test")
def test_detect_os_mock_windows_from_linux():
    with (
        patch("platform.system", return_value=OS.WINDOWS.value),
        patch("platform.release", return_value="10"),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.WINDOWS, WindowsVersions.WIN10.value)


@pytest.mark.skipif(platform.system().lower() != OS.LINUX.value, reason=OS.LINUX.value + "-only test")
def test_detect_os_mock_macos_from_linux():
    with (
        patch("platform.system", return_value="Darwin"),
        patch("platform.mac_ver", return_value=("14.5", ("", "", ""), "")),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.MACOS, "v14.5")


# =========================================================
# MACOS
# =========================================================


@pytest.mark.skipif(platform.system().lower() != OS_PLATFORM_MACOS, reason=OS.MACOS.value + "-only test")
def test_detect_os_real_macos():
    result = detect_os()

    assert result.error is None
    assert result.value is not None

    detected_os, version = result.value

    assert detected_os == OS.MACOS
    assert version[0] == VERSION_STRING_PREFIX


@pytest.mark.skipif(platform.system().lower() != OS_PLATFORM_MACOS, reason=OS.MACOS.value + "-only test")
def test_detect_os_mock_windows_from_macos():
    with (
        patch("platform.system", return_value=OS.WINDOWS.value),
        patch("platform.release", return_value="10"),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.WINDOWS, WindowsVersions.WIN10.value)


@pytest.mark.skipif(platform.system().lower() != OS_PLATFORM_MACOS, reason=OS.MACOS.value + "-only test")
def test_detect_os_mock_linux_from_macos():
    os_release_content = f"""
ID={UBUNTU_STRING_PREFIX}
VERSION_ID="24.04"
"""

    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.release", return_value="6.8.0"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=os_release_content),
    ):
        result = detect_os()

    assert result.error is None
    assert result.value == (OS.LINUX, UbuntuVersions.UBUNTU_24_04.value)


# =========================================================
# UNSUPPORTED OS
# =========================================================


def test_detect_os_unsupported():
    with patch("platform.system", return_value="Solaris"):
        result = detect_os()

    assert result.value is None
    assert result.error == "Unsupported OS: solaris"


# =========================================================
# LINUX EDGE CASES
# =========================================================


def test_detect_os_linux_without_os_release():
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.release", return_value="6.8.0"),
        patch("pathlib.Path.exists", return_value=False),
    ):
        result = detect_os()

    assert result.error is not None


def test_detect_os_linux_missing_version_id():
    os_release_content = f"""
ID={UBUNTU_STRING_PREFIX}
"""

    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.release", return_value="6.8.0"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=os_release_content),
    ):
        result = detect_os()

    assert result.error is not None


def test_detect_os_linux_missing_both_id_and_version():
    os_release_content = """
NAME="Ubuntu"
PRETTY_NAME="Ubuntu 24.04"
"""

    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.release", return_value="6.8.0"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=os_release_content),
    ):
        result = detect_os()

    assert result.error is not None
