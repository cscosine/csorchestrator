import sys
from pathlib import Path
from typing import cast

from csorchestrator.portable.deployments import create_deployment_archives

build_dir = cast(Path, "__BUILD_DIR__")  # fmt: skip
build_config = "__BUILD_CONFIG__"
project_name = "__PROJECT_NAME__"
project_name_and_version = "__PROJECT_NAME_VERSION__"
variant = "__VARIANT__"
output_dir = cast(Path, "__OUTPUT_DIR__")  # fmt: skip

errors_list = create_deployment_archives(
    build_dir=Path(build_dir),
    build_config=build_config,
    project_name=project_name,
    project_name_and_version=project_name_and_version,
    variant=variant,
    output_dir=Path(output_dir),
)

if len(errors_list) > 0:
    for e in errors_list:
        print(e)
    sys.exit("ERROR: archiving the deployments")
