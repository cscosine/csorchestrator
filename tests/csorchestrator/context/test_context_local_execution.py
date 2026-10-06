from pathlib import Path

import pytest

from csorchestrator.frontend.local_execution.validate_and_execute import create_os_and_path


def test_local_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # change local directory to tmp_path
    monkeypatch.chdir(tmp_path)

    cr = create_os_and_path(Path("./"))

    assert cr.has_result()
    assert not cr.report.has_errors()
    assert cr.result is not None
    assert cr.result.path == tmp_path.resolve()
