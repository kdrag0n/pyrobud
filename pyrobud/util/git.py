import sys
from pathlib import Path

# DeepSource doesn't understand lazily-evaluated type hints. skipcq: PYL-W0611
from typing import Optional

try:
    import git

    have_git = True
except ImportError:
    git = None
    have_git = False


OFFICIAL_REPO = "kdrag0n/pyrobud"


class LazyRepo:
    initialized: bool
    repo: "Optional[git.Repo]"

    def __init__(self) -> None:
        self.initialized = not have_git
        self.repo = None

    def get(self) -> "Optional[git.Repo]":
        if not self.initialized:
            try:
                self.repo = git.Repo(Path(sys.argv[0]).parent, search_parent_directories=True, odbt=git.GitDB)
            # Silence a bogus pylint error
            # pylint: disable=no-member
            except git.exc.InvalidGitRepositoryError:
                pass

            self.initialized = True

        return self.repo


_repo = LazyRepo()


def get_repo() -> "Optional[git.Repo]":
    return _repo.get()


def get_current_remote() -> "Optional[git.Remote]":
    repo = get_repo()
    if not repo:
        return None

    remote_ref = repo.active_branch.tracking_branch()
    if remote_ref is None:
        return None

    return repo.remote(remote_ref.remote_name)


def is_dirty() -> bool:
    # Assume non-Git instances are clean, e.g. when installed with pip
    repo = get_repo()
    if not repo:
        return False

    return repo.is_dirty()


def is_official() -> bool:
    # Assume non-Git instances are official, e.g. when installed with pip
    repo = get_repo()
    if not repo:
        return True

    # Dirty working tree breaks official status
    if repo.is_dirty():
        return False

    # Assume Git instances without a tracking remote are unofficial
    remote = get_current_remote()
    if not remote:
        return False

    return all(OFFICIAL_REPO in url for url in remote.urls)
