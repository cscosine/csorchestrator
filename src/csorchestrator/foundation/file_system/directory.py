# execution context
import os
import tempfile
from pathlib import Path
from typing import TypeAlias

from csorchestrator.foundation.core.expected import Expected

ExpectedPathOrError: TypeAlias = Expected[Path, str]


def ensure_directory_exists_or_create_and_is_usable(path: Path) -> ExpectedPathOrError:
    try:
        # Expand ~ and environment variables, then resolve
        p = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    except Exception as e:
        return Expected[Path, str].make_error(f"Invalid path '{path}': {e}")

    try:
        # Create directory if it does not exist
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return Expected[Path, str].make_error(f"Failed to create directory '{p}': {e}")

    # Ensure it's actually a directory
    if not p.is_dir():
        return Expected[Path, str].make_error(f"Path exists but is not a directory: '{p}'")

    # Check readability & writability by attempting real operations
    try:
        # Create a temp file inside the directory
        with tempfile.NamedTemporaryFile(dir=p, delete=True) as tmp:
            tmp.write(b"test")
            tmp.flush()

        # Try creating a subdirectory
        test_subdir = p / "__test_subdir__"
        test_subdir.mkdir(exist_ok=True)
        test_subdir.rmdir()

    except Exception as e:
        return Expected[Path, str].make_error(f"Directory '{p}' is not writable or accessible: {e}")

    return Expected[Path, str].make_value(p)
