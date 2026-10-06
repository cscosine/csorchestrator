import sys
from pathlib import Path
from typing import cast

from csorchestrator.portable.release_manifest import (
    load_release_manifest_single_variant_and_prepare_archive,
)

input_full_path = cast(Path, "__INPUT_FULL_PATH__")  # fmt: skip
project_name_and_version = "__PROJECT_NAME_VERSION__"
context_os_architecture_compiler_generator_string = "CONTEXT_OS_ARCHITECTURE_COMPILER_GENERATOR_STRING"
input_base_dir = cast(Path, "__BASE_DIR_PATH__")  # fmt: skip

errors_list = load_release_manifest_single_variant_and_prepare_archive(
    input_full_path=input_full_path,
    project_name_and_version=project_name_and_version,
    context_os_architecture_compiler_generator_string=context_os_architecture_compiler_generator_string,
    input_base_dir=input_base_dir.resolve(),
)

if len(errors_list) > 0:
    for e in errors_list:
        print(e)
    sys.exit("ERROR: getting package versions")
