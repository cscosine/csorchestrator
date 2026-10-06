import logging
from pathlib import Path

import pytest

from csorchestrator.foundation.git.repo_clone_checkout import try_git_clone_checkout
from csorchestrator.foundation.git.resolve_url import RepoUrlParts
from tests.csorchestrator.repo_test_data_config import RepoTestData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _check_status(target_path: Path, expected_content: str) -> None:
    cfg = RepoTestData()
    with open(target_path / cfg.file_to_verify, encoding="utf-8") as f:
        first_line = f.readline().strip()

    assert first_line == expected_content


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_branch_main(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(), repo_ref=cfg.main_branch, target_path=target_path, depth_one=depth_one
    )

    assert not r.has_errors()
    _check_status(target_path, cfg.expected_content_main)


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_branch_dev(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.dev_branch,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert not r.has_errors()
    _check_status(target_path, cfg.expected_content_dev)


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_tag(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(), repo_ref=cfg.tag, target_path=target_path, depth_one=depth_one
    )

    assert not r.has_errors()
    _check_status(target_path, cfg.expected_content_tag)


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_sha(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.initial_commit_sha,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert not r.has_errors()
    _check_status(target_path, cfg.expected_content_initial)


# not allowed cases
@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_non_existing_ref(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.non_existing_ref,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert r.has_errors()


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_branch_origin_main(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.origin_main_branch,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert r.has_errors()


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_head(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(), repo_ref=cfg.head, target_path=target_path, depth_one=depth_one
    )

    assert r.has_errors()


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_refs_heads_main(tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.refs_heads_main,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert r.has_errors()


@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_repo_refs_remote_origin_main(
    tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool
) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.refs_remote_origin_main,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert r.has_errors()


# coverage for defensive code in case of unknown ref type, which should never happen but let's be defensive anyway
@pytest.mark.slow
@pytest.mark.git
@pytest.mark.parametrize("depth_one", [True, False])
def test_try_git_clone_checkout_unknown_ref_type(
    tmp_path: Path, repo_url: RepoUrlParts, depth_one: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = RepoTestData()

    target_path = tmp_path / cfg.destination_folder

    assert not target_path.is_dir()

    # monkeypatch the resolve_ref_type to return an unknown type
    from csorchestrator.foundation.git import repo_clone_checkout as mod

    def mock_resolve_ref_type(repo, ref):
        return "unknown_ref_type"

    monkeypatch.setattr(mod, "resolve_ref_type", mock_resolve_ref_type)

    r = try_git_clone_checkout(
        repo_url=repo_url.repo_url(),
        repo_ref=cfg.main_branch,
        target_path=target_path,
        depth_one=depth_one,
    )

    assert r.has_errors()
    assert "Unknown ref type for" in r.errors[0]
