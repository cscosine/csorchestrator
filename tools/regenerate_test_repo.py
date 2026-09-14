#!/usr/bin/env python3
import os
import shutil
import tempfile

from git import Repo

from csorchestrator.foundation.core.report import Report
from csorchestrator.foundation.git.resolve_url import RepoUrlParts, select_https_or_ssh_url_resolve_token_name_on_env
from csorchestrator.frontend.reporters.report_reporter import repo_to_reporter_sink

# keep these values aligned with the ones in tests/csorchestrator/utils/git/repo_config.py
TOKEN_NAME: str = "ACTIONS_ORG_ACCESS"
HTTPS_URL_TEMPLATE: RepoUrlParts = RepoUrlParts("https://{token}@github.com/", "cscosine", "csOrchestratorTestRepo.git")
SSH_URL: RepoUrlParts = RepoUrlParts("git@github.com:", "cscosine", "csOrchestratorTestRepo.git")
STATUS_FILE: str = "STATUS.txt"


def write_status(repo_path: str, value: str) -> None:
    with open(os.path.join(repo_path, STATUS_FILE), "w", encoding="utf-8") as f:
        f.write(value)


def write_readme(repo_path: str) -> None:
    readme_path = os.path.join(repo_path, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "# csOrchestratorTestRepo\n"
            "\n\n"
            "A test repository used to check the functionality of csOrchestrator\n\n"
            "It contains a STATUS.txt file and has\n\n"
            "- main branch\n"
            '- a initial commit, STATUS.txt contains "initial"\n'
            '- a second commit with tag v0.0.1, STATUS.txt contains "tag"\n'
            '- dev branch on top of main, STATUS.txt contains "dev"\n'
            "\n"
            "and its content should be ecaxtly what the readme says, bc I am using it to make tests in my projects!\n"
        )


def commit(repo: Repo, message: str, report: Report) -> str:
    repo.git.add(A=True)
    repo.index.commit(message)
    sha = repo.head.commit.hexsha
    report.append_info(f"Committed: {message} ({sha})")
    assert isinstance(sha, str)  # mypy type checking hint, it is actually a str but gitpython types are not correct
    return sha


def push_all(repo: Repo, report: Report) -> None:
    origin = repo.remote(name="origin")

    report.append_info("Force pushing main")
    origin.push(refspec="main:main", force=True)

    report.append_info("Force pushing dev")
    origin.push(refspec="dev:dev", force=True)

    report.append_info("Force pushing tags")
    origin.push(tags=True, force=True)


def build_repo(repo_path: str, report: Report) -> str:
    repo = Repo.init(repo_path)
    report.append_info("Initialized git repo")

    # ---------------- main branch ----------------
    repo.git.checkout("-b", "main")

    write_status(repo_path, "initial")
    write_readme(repo_path)
    commit(repo, "initial commit", report)
    initial_sha = repo.head.commit.hexsha

    write_status(repo_path, "tag")
    commit(repo, "second commit", report)

    repo.create_tag("v0.0.1")
    report.append_info("Created tag v0.0.1")

    # ---------------- dev branch ----------------
    repo.git.checkout("-b", "dev")

    write_status(repo_path, "dev")
    commit(repo, "dev commit", report)

    assert isinstance(
        initial_sha, str
    )  # mypy type checking hint, it is actually a str but gitpython types are not correct
    return initial_sha


def main() -> int:
    report = Report()

    url, selected = select_https_or_ssh_url_resolve_token_name_on_env(
        HTTPS_URL_TEMPLATE,
        SSH_URL,
        TOKEN_NAME,
    )

    report.append_info(f"Selected remote: {selected}, url: {url.repo_url()}")

    tmp_dir = tempfile.mkdtemp(prefix="csorchestrator_repo_")

    try:
        repo = Repo.init(tmp_dir)
        _ = repo.create_remote("origin", url)

        initial_sha = build_repo(tmp_dir, report)
        push_all(repo, report)

        if report.has_errors():
            report.append_error("Repository regeneration failed")
            repo_to_reporter_sink(report)
            return 1

        report.append_info("Repository successfully regenerated")
        repo_to_reporter_sink(report)

        # REQUIRED OUTPUT
        print(
            f"Main initial commit SHA: {initial_sha}, "
            "please update tests/csorchestrator/utils/git/repo_config.py accordingly"
        )

        return 0

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
