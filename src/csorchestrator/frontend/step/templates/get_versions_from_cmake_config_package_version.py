import sys
from pathlib import Path
from typing import cast

from csorchestrator.portable.package_version import CMakeConfigPackageVersionGrep, PackageVersion
from csorchestrator.portable.release_manifest import get_package_versions_and_write_single_variant_manifest

repos_config_file_list = cast(list[CMakeConfigPackageVersionGrep], "__REPOS_CONFIG_FILE_LIST__")  # fmt: skip
repos_auto_search_list = cast(list[str], "__REPOS_AUTO_SEARCH_LIST__")  # fmt: skip
repos_version = cast(list[PackageVersion], "__REPOS_VERSION__")  # fmt: skip
base_install_dir = cast(Path, "__BASE_INSTALL_DIR__")  # fmt: skip
install_subdir = cast(Path, "__INSTALL_SUB_DIR__")  # fmt: skip
variant_string = "__VARIANT_STRING__"  # fmt: skip
project_name = "__PROJECT_NAME__"  # fmt: skip
project_version = "__PROJECT_VERSION__"  # fmt: skip
output_file = cast(Path, "__OUTPUT_FILE__")  # fmt: skip

errors_list = get_package_versions_and_write_single_variant_manifest(
    repos_config_file_list=repos_config_file_list,
    repos_auto_search_list=repos_auto_search_list,
    repos_version=repos_version,
    base_install_dir=base_install_dir,
    install_subdir=install_subdir,
    variant_string=variant_string,
    project_name=project_name,
    project_version=project_version,
    output_file=output_file,
)

if len(errors_list) > 0:
    for e in errors_list:
        print(e)
    sys.exit("ERROR: getting package versions")
