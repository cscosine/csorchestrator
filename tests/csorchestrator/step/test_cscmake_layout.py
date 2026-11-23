"""The standalone csCMake layout check: the workspace root a project declares against the recipe's base_target_dir."""

import json
from pathlib import Path

from csorchestrator.application.recipes.checkout_build import build_repos
from csorchestrator.application.recipes.create_orchestrator import create_default_orchestrator
from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig
from csorchestrator.frontend.step.step_cmake_command import StepCMakeWorkflow
from csorchestrator.portable.cscmake_layout import check_standalone_workspace, standalone_workspace_root


def write_setup(source_dir: Path, *includes: str) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "csCMakeProjectSetup.json").write_text(json.dumps({"version": 10, "include": list(includes)}))


def test_standalone_root_from_the_include(tmp_path: Path) -> None:
    write_setup(tmp_path, "${sourceDir}/_csw/csCMake/presets/layout/standalone.json")
    assert standalone_workspace_root(tmp_path) == tmp_path / "_csw"


def test_standalone_short_root(tmp_path: Path) -> None:
    write_setup(tmp_path, "${sourceDir}/ws/csCMake/presets/layout/standalone-short.json")
    assert standalone_workspace_root(tmp_path) == tmp_path / "ws"


def test_other_layouts_and_no_file_are_not_checked(tmp_path: Path) -> None:
    assert standalone_workspace_root(tmp_path) is None
    write_setup(tmp_path, "${sourceParentDir}/csCMake/presets/layout/sibling.json")
    assert standalone_workspace_root(tmp_path) is None
    write_setup(tmp_path, "$penv{CSCMAKE_ROOT}/presets/layout/env.json")
    assert standalone_workspace_root(tmp_path) is None


def test_unreadable_setup_is_not_checked(tmp_path: Path) -> None:
    (tmp_path / "csCMakeProjectSetup.json").write_text("{ not json")
    assert standalone_workspace_root(tmp_path) is None


def test_matching_base_target_dir_passes(tmp_path: Path) -> None:
    write_setup(tmp_path, "${sourceDir}/_csw/csCMake/presets/layout/standalone.json")
    assert check_standalone_workspace(tmp_path / ".", tmp_path / "_csw") is None


def test_mismatching_base_target_dir_names_both(tmp_path: Path) -> None:
    write_setup(tmp_path, "${sourceDir}/_csw/csCMake/presets/layout/standalone.json")
    error = check_standalone_workspace(tmp_path, tmp_path / "workspace")
    assert error is not None
    assert "_csw" in error and "workspace" in error and "base_target_dir" in error


def test_build_repos_gives_the_own_sources_the_workspace_root() -> None:
    o = create_default_orchestrator(name="app", version="1.0.0", base_install_dir=Path("_csw/install"))
    build_repos(o, base_target_dir=Path("_csw"), build_self=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID)
    steps = [s for phase in o.phases for s in phase.steps if isinstance(s, StepCMakeWorkflow)]
    own = [s for s in steps if s.source_dir == "."]
    assert len(own) == 1 and own[0].workspace_root == "_csw"
