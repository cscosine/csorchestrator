import sys
from pathlib import Path
from typing import cast

from csorchestrator.portable.deployments import DeploymentArchives, DeploymentRun, run_deployment

build_dir = cast(Path, "__BUILD_DIR__")  # fmt: skip
build_config = "__BUILD_CONFIG__"
deployment = "__DEPLOYMENT__"
archives_dir = cast(Path, "__ARCHIVES_DIR__")  # fmt: skip
project_name = "__PROJECT_NAME__"
project_name_and_version = "__PROJECT_NAME_VERSION__"
variant = "__VARIANT__"
commands = cast(dict[str, list[str]], {})  # by OS: linux, windows, macos
clean_environment = True
install_system_requirements = False
expect_exit_code = 0
timeout_seconds = 120.0

os_name = "windows" if sys.platform == "win32" else "macos" if sys.platform == "darwin" else "linux"
if os_name not in commands:
    print(f"deployment {deployment}: no command on {os_name}, not run")
    sys.exit(0)

errors_list = run_deployment(
    Path(build_dir),
    build_config,
    DeploymentRun(
        deployment=deployment,
        command=commands[os_name],
        clean_environment=clean_environment,
        install_system_requirements=install_system_requirements,
        expect_exit_code=expect_exit_code,
        timeout_seconds=timeout_seconds,
    ),
    DeploymentArchives(Path(archives_dir), project_name, project_name_and_version, variant),
)

if len(errors_list) > 0:
    for e in errors_list:
        print(e)
    sys.exit(f"ERROR: running the deployment {deployment}")
