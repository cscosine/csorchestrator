import os  # noqa: F401 keep even if locally unused, necessary with variable subst
import sys
from pathlib import Path
from typing import cast

from csorchestrator.portable.release_manifest import (
    PublishPackageMode,  # noqa: F401 keep even if locally unused, necessary after variable subst
    ReposPublishConfigDict,
    collect_release_manifest_single_variant_and_prepare_manifest,
)

input_folder_base = cast(Path, "_")
input_manifest_path_variant = cast(list[tuple[Path, str]], "_")
output_manifest_filename = cast(Path, "_")
project_name = "_"
project_version = "_"
base_path_additional_files = cast(Path, "_")
list_additional_files = cast(list[Path], "_")
output_folder_additional_files = cast(Path, "_")
output_bundle_file_name = cast(Path, "_")
repo_publish_config_dict = cast(ReposPublishConfigDict, "_")
header_only_variants_sources = cast(dict[str, str], "_")

errors_list = collect_release_manifest_single_variant_and_prepare_manifest(
    input_folder_base=input_folder_base,
    input_manifest_path_variant=input_manifest_path_variant,
    output_manifest_filename=output_manifest_filename,
    project_name=project_name,
    project_version=project_version,
    base_path_additional_files=base_path_additional_files,
    list_additional_files=list_additional_files,
    output_folder_additional_files=output_folder_additional_files,
    output_bundle_file_name=output_bundle_file_name,
    repo_publish_config_dict=repo_publish_config_dict,
    header_only_variants_sources=header_only_variants_sources,
    archive_files_are_in_context_based_folder=True,
)

if len(errors_list) > 0:
    for e in errors_list:
        print(e)
    sys.exit("ERROR: getting package versions")
