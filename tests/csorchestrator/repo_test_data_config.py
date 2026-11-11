from dataclasses import dataclass

from csorchestrator.foundation.git.resolve_url import RepoUrlParts

# note: the test repo can be regenerated with the tool in tools/regenerate_test_repo.py,
# after which the sha of the initial_commit_sha variable must be updated in this file accordingly


@dataclass(frozen=True)
class RepoTestData:
    main_branch: str = "main"
    origin_main_branch: str = "origin/main"
    dev_branch: str = "dev"
    tag: str = "v0.0.1"
    non_existing_ref: str = "ref_does_not_exists"
    head: str = "HEAD"
    initial_commit_sha: str = "063ee5ddc414553e32b234170542a717cfe9d087"
    refs_heads_main: str = "refs/heads/main"
    refs_remote_origin_main: str = "refs/remotes/origin/main"

    destination_folder: str = "csOrchestratorTestRepo"
    repo_name: str = "csOrchestratorTestRepo"

    file_to_verify: str = "STATUS.txt"
    expected_content_main: str = "tag"
    expected_content_tag: str = "tag"
    expected_content_dev: str = "dev"
    expected_content_initial: str = "initial"

    # if the test is executed on github actions, we need a token to access it
    # "ACTIONS_ORG_ACCESS" needs to be in the secrets of the csOrchestratorTestRepo
    # and in the pytest job config as
    #      - name: Run tests with coverage
    #        env:
    #          ACTIONS_ORG_ACCESS: ${{ secrets.ACTIONS_ORG_ACCESS }}
    #        run: |
    #          pytest [...]
    token_name: str = "ACTIONS_ORG_ACCESS"
    https_url_template: RepoUrlParts = RepoUrlParts(
        "https://x-access-token:{token}@github.com/", "cscosine", "csOrchestratorTestRepo.git"
    )
    ssh_url: RepoUrlParts = RepoUrlParts("git@github.com:", "cscosine", "csOrchestratorTestRepo.git")
