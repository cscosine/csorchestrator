import os
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.github_workflow_translation.github_step_interface import GithubStepInterface
from csorchestrator.frontend.github_workflow_translation.github_workflow_steps_translations import (
    StepGitHubAction,
    StepRunCommand,
)


@dataclass
class DownloadGithubFileEntry:
    """An asset of a GitHub release."""

    base_url: str
    org: str
    git_repo: str
    tag: str
    asset_filename: str

    def to_string(self) -> str:
        return urljoin(
            self.base_url,
            "/".join([self.org, self.git_repo, self.tag, self.asset_filename]),
        )

    def is_equal(self, other: "DownloadGithubFileEntry") -> bool:
        return (
            self.base_url == other.base_url
            and self.org == other.org
            and self.git_repo == other.git_repo
            and self.tag == other.tag
            and self.asset_filename == other.asset_filename
        )

    def is_incompatible(self, other: "DownloadGithubFileEntry") -> bool:
        return (
            self.base_url == other.base_url
            and self.org == other.org
            and self.git_repo == other.git_repo
            and self.asset_filename == other.asset_filename
            # but on different tag
            and self.tag != other.tag
        )


def create_github_release_download_url(
    entry: DownloadGithubFileEntry,
) -> str:
    """Create the download URL of an asset published in a GitHub release."""

    return urljoin(
        entry.base_url,
        "/".join([entry.org, entry.git_repo, "releases", "download", entry.tag, entry.asset_filename]),
    )


# ---------------------------------------------------------
# local execution
# ---------------------------------------------------------


def download_github_release_asset(entry: DownloadGithubFileEntry, target_filename: Path) -> Report:
    """Download the asset to target_filename (its folder must exist); an error if missing or empty."""
    report = Report()

    download_url = create_github_release_download_url(entry)
    report.append_info("download URL " + download_url + " to " + target_filename.as_posix())

    try:
        request.urlretrieve(download_url, target_filename)
    except HTTPError as e:
        report.append_error(f"HTTP error: {e.code} - {e.reason}")
        return report
    except URLError as e:
        report.append_error(f"Network error: {e.reason}")
        return report

    if not os.path.exists(target_filename):
        report.append_error("Download failed: file does not exist")
        return report

    if os.path.getsize(target_filename) == 0:
        report.append_error("Download failed: file is empty")
        return report

    return report


def extract_tar_gz(archive: Path, extract_dir: Path) -> Report:
    """Extract a .tar.gz into extract_dir; members with an absolute path or '..' are an error (nothing extracted)."""
    report = Report()

    if not tarfile.is_tarfile(archive):
        report.append_error(f"Not a valid tar archive: {archive}")
        return report

    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            for m in members:
                p = PurePosixPath(m.name)
                if p.is_absolute() or ".." in p.parts:
                    report.append_error(f"Unsafe path {m.name} in archive {archive}")
                    return report
            if hasattr(tarfile, "data_filter"):
                tar.extractall(extract_dir, members=members, filter="data")
            else:  # Python < 3.11.4
                tar.extractall(extract_dir, members=members)
    except tarfile.TarError as e:
        report.append_error(f"Extraction failed: {archive}: {e}")
        return report

    return report


def download_and_extract_github_release_asset(entry: DownloadGithubFileEntry, target_dir: Path) -> Report:
    """Download the .tar.gz asset into target_dir (it must exist), extract it there, delete the archive."""
    report = Report()

    archive = target_dir / Path(entry.asset_filename).name
    report.append_report(download_github_release_asset(entry, archive))
    if report.has_errors():
        return report

    report.append_report(extract_tar_gz(archive, target_dir))
    if report.has_errors():
        return report

    os.remove(archive)
    return report


# ---------------------------------------------------------
# github workflow
# ---------------------------------------------------------


def github_release_download_and_extract_steps(
    name: str,
    entry: DownloadGithubFileEntry,
    target_dir: str,
) -> list[GithubStepInterface]:
    """
    Workflow steps: download the .tar.gz asset into target_dir, extract it there, delete the archive.

    entry.asset_filename can be a workflow expression (e.g. the output of a previous step).
    """
    archive = f"{target_dir}/{entry.asset_filename}"

    return [
        StepGitHubAction(
            name=name + " download tar.gz",
            uses="robinraju/release-downloader@v1.13",
            with_list={
                "repository": f"{entry.org}/{entry.git_repo}",
                "tag": entry.tag,
                "fileName": entry.asset_filename,
                "out-file-path": target_dir,
            },
        ),
        StepRunCommand(
            name=name + " extract tar.gz",
            shell_type="bash",
            run=[f"tar -xzf {archive} -C {target_dir}", f"rm -f {archive}"],
        ),
    ]
