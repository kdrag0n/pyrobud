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
        _repo = git.Repo(os.path.dirname(sys.argv[0]), search_parent_directories=True)
    # Silence a bogus pylint error
    # pylint: disable=no-member
    except git.exc.InvalidGitRepositoryError:
        # No Git repository
        pass

    _repo_initialized = True
    return _repo
