from shutil import which

import pytest


def has_tool(name: str) -> bool:
    return which(name) is not None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_all = config.getoption("--run-all")
    if run_all:
        return  # 👈 CRITICAL: disable ALL requires logic

    for item in items:
        marker = item.get_closest_marker("requires")
        if not marker:
            continue

        # supports multiple args: @requires("cl")
        tool = marker.args[0]

        if not has_tool(tool):
            # local mode → SKIP (--run-all, as CI: run, and fail when the tool is missing)
            item.add_marker(pytest.mark.skip(reason=f"Required tool missing: {tool}"))
