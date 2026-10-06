import platform
import stat
from pathlib import Path

import pytest

from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.foundation.file_system.directory import ensure_directory_exists_or_create_and_is_usable


def test_creates_directory(tmp_path: Path) -> None:
    target = tmp_path / "new_dir"

    cr = ensure_directory_exists_or_create_and_is_usable(target)

    assert cr.value
    assert not cr.error
    assert cr.value == target.resolve()
    assert target.exists()
    assert target.is_dir()


def test_local_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # change local directory to tmp_path
    monkeypatch.chdir(tmp_path)

    cr = ensure_directory_exists_or_create_and_is_usable(Path("./"))

    assert cr.value
    assert not cr.error
    assert cr.value == tmp_path.resolve()


def test_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # change local directory to tmp_path
    monkeypatch.chdir(tmp_path)

    cr = ensure_directory_exists_or_create_and_is_usable(Path("relative_dir"))

    assert cr.value
    assert not cr.error
    assert cr.value == (tmp_path / "relative_dir").resolve()


def test_expand_user_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DIR", str(tmp_path))

    cr = ensure_directory_exists_or_create_and_is_usable(Path("$TEST_DIR/env_dir"))

    assert cr.value
    assert not cr.error
    assert cr.value == (tmp_path / "env_dir").resolve()


def test_existing_directory(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()

    cr1 = ensure_directory_exists_or_create_and_is_usable(target)
    cr2 = ensure_directory_exists_or_create_and_is_usable(target)

    assert cr1.value
    assert not cr1.error

    assert cr2.value
    assert not cr2.error

    assert cr1.value == cr2.value


def test_path_is_file_dir_creation_fails(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    cr = ensure_directory_exists_or_create_and_is_usable(file_path)
    assert not cr.value
    assert cr.error
    assert "Failed to create directory" in cr.error


def test_path_is_file_dir_creation_patched(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    # Prevent mkdir from interfering with the test
    def fake_mkdir(*args, **kwargs):
        return None

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    cr = ensure_directory_exists_or_create_and_is_usable(file_path)
    assert not cr.value
    assert cr.error
    assert "not a directory" in cr.error


def test_directory_is_writable(tmp_path: Path) -> None:
    cr = ensure_directory_exists_or_create_and_is_usable(tmp_path / "writable")
    assert cr.value
    assert not cr.error

    assert cr.value is not None
    result_path = cr.value

    test_file = result_path / "test.txt"
    test_file.write_text("hello")

    assert test_file.exists()


@pytest.mark.skipif(
    platform.system().lower() == OS.WINDOWS.value, reason="Permission test unreliable on " + OS.WINDOWS.value
)
def test_permission_error(tmp_path: Path) -> None:
    target = tmp_path / "restricted"
    target.mkdir()

    # Remove write permissions
    target.chmod(stat.S_IREAD)

    cr = ensure_directory_exists_or_create_and_is_usable(target)
    assert not cr.value
    assert cr.error

    # Restore permissions so pytest can clean up
    target.chmod(stat.S_IWUSR | stat.S_IREAD)


# test that a a resolution failure with env variable fail is hard, let's do it via mocking
def test_resolve_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_resolve(self):
        raise RuntimeError("resolution failed")

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    cr = ensure_directory_exists_or_create_and_is_usable(Path("some/path"))
    assert not cr.value
    assert cr.error
