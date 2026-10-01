from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from csorchestrator.frontend.cscmake_presets.supported_variants import BuildConfig


class PublishPackageMode(Enum):
    ON_VARIANT = "ON_VARIANT"
    HEADERS_ONLY = "HEADERS_ONLY"


@dataclass(frozen=True)
class RepoRefBuildPublishConfig:
    repo_ref: str
    build_config: BuildConfig | None
    publish_mode: PublishPackageMode = PublishPackageMode.ON_VARIANT
    # invariant: if build_config is None, publish_mode is ignored


RepoRefBuildPublishConfigDict: TypeAlias = dict[str, RepoRefBuildPublishConfig]

# individual simpler types
ReposBuildConfigDict: TypeAlias = dict[str, BuildConfig | None]


def extract_build_config_dict(repos: RepoRefBuildPublishConfigDict) -> ReposBuildConfigDict:
    ret: ReposBuildConfigDict = {}
    for repo, config in repos.items():
        ret[repo] = config.build_config
    return ret


ReposRefDict: TypeAlias = dict[str, str]


def extract_repo_ref_dict(repos: RepoRefBuildPublishConfigDict) -> ReposRefDict:
    ret: ReposRefDict = {}
    for repo, config in repos.items():
        ret[repo] = config.repo_ref
    return ret


ReposPublishConfigDict: TypeAlias = dict[str, PublishPackageMode]


def extract_repo_publish_config_dict(repos: RepoRefBuildPublishConfigDict) -> ReposPublishConfigDict:
    ret: ReposPublishConfigDict = {}
    for repo, config in repos.items():
        ret[repo] = config.publish_mode
    return ret


def extract_repo_list_build_non_none(repos: ReposBuildConfigDict) -> list[str]:
    ret: list[str] = []
    for repo, build_config in repos.items():
        if build_config is not None:
            ret.append(repo)
    return ret
