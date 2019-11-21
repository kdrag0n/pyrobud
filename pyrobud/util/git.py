import os
import sys

have_git = True
try:
    import git
except ImportError:
    have_git = False

_repo_initialized = False
_repo = None


def get_repo():
    global _repo_initialized
    global _repo

    if _repo_initialized:
        return _repo

    # Return None if Git isn't available
    if not have_git:
        _repo_initialized = True
        return _repo

    # Attempt to get a reference to the Git repository
    try:
        _repo = git.Repo(os.path.dirname(sys.argv[0]), search_parent_directories=True, odbt=git.GitDB)
    # Silence a bogus pylint error
    # pylint: disable=no-member
    except git.exc.InvalidGitRepositoryError:
        # No Git repository
        pass

    _repo_initialized = True
    return _repo


def get_current_remote():
    repo = get_repo()
    if not repo:
        return None

    remote_ref = repo.active_branch.tracking_branch()
    if remote_ref is None:
        return None

    return repo.remote(remote_ref.remote_name)


def is_official():
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

    # Unofficial remote repository name breaks official status
    for url in remote.urls:
        if "kdrag0n/pyrobud" not in url:
            return False

    # We're most likely running official code if the above checks passed
    return True
