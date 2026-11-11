from csorchestrator.frontend.step.github_release_download import DownloadGithubFileEntry
from csorchestrator.frontend.step.step_get_repository import StepGetRepositoryGitHub


def create_cscmake_release_archive(version: str, org: str = "cscosine") -> DownloadGithubFileEntry:
    """The package of a csCMake release (tag v<version>), e.g. "1.0.0-rc1": its content is in a folder csCMake/."""
    return DownloadGithubFileEntry(
        base_url=StepGetRepositoryGitHub.GITHUB_BASE_URL_HTTPS,
        org=org,
        git_repo="csCMake",
        tag=f"v{version}",
        asset_filename=f"csCMake-{version}.tar.gz",
    )
