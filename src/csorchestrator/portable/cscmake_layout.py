"""The csCMake layout a source folder declares, and its workspace root (standard library only).

A csCMake project names its layout in ``csCMakeProjectSetup.json``: an include
``<csCMake>/presets/layout/<layout>.json``. In the ``standalone`` layouts csCMake is ``<workspace root>/csCMake``
and the workspace root is inside the project (``${sourceDir}/...``), so the include gives it. The recipe's
``base_target_dir`` (checkouts, csCMake, builds, installs) must be that folder: else csCMake builds and installs where
csorchestrator does not look.
"""

import json
import re
from pathlib import Path

PROJECT_SETUP_FILE = "csCMakeProjectSetup.json"
_LAYOUT_INCLUDE = re.compile(r"^(?P<cscmake>.*)/presets/layout/(?P<layout>[A-Za-z0-9_-]+)\.json$")


def standalone_workspace_root(source_dir: Path) -> Path | None:
    """The workspace root of ``source_dir`` when its ``csCMakeProjectSetup.json`` includes a ``standalone`` layout
    (``<root>/csCMake/presets/layout/standalone*.json``, ``${sourceDir}`` expanded), else None (no file, another layout,
    an include it cannot read)."""
    setup_file = source_dir / PROJECT_SETUP_FILE
    if not setup_file.is_file():
        return None
    try:
        includes = json.loads(setup_file.read_text(encoding="utf-8")).get("include", [])
    except (OSError, ValueError, AttributeError):
        return None
    for include in includes if isinstance(includes, list) else []:
        match = _LAYOUT_INCLUDE.match(str(include))
        if match is None or not match.group("layout").startswith("standalone"):
            continue
        cscmake = match.group("cscmake")
        if not cscmake.startswith("${sourceDir}/") or not cscmake.endswith("/csCMake"):
            return None
        relative = cscmake[len("${sourceDir}/") : -len("/csCMake")]
        return source_dir / relative
    return None


def check_standalone_workspace(source_dir: Path, workspace_root: Path) -> str | None:
    """An error when ``source_dir`` declares a ``standalone`` layout whose workspace root is not ``workspace_root``
    (the recipe's ``base_target_dir``), else None."""
    layout_root = standalone_workspace_root(source_dir)
    if layout_root is None or layout_root.resolve() == workspace_root.resolve():
        return None
    return (
        f"{source_dir / PROJECT_SETUP_FILE} declares a standalone csCMake layout with the workspace in {layout_root}, "
        f"but the recipe's base_target_dir is {workspace_root}: csCMake would build and install where csorchestrator "
        "does not look. Make them the same folder."
    )
