import logging
import os
import pkg_resources
import sys

log = logging.getLogger(__name__)

have_git = True
try:
    import git
except ImportError:
    have_git = False


def get_commit():
    if have_git:
        # Attempt to get the current Git commit
        try:
            repo = git.Repo(os.path.dirname(sys.argv[0]), search_parent_directories=True)
            return repo.head.object.hexsha[:8]
        # Silence a bogus pylint error
        # pylint: disable=no-member
        except git.exc.InvalidGitRepositoryError:
            # No Git repository
            pass
        except Exception as e:
            log.warn("Error querying Git commit", exc_info=e)

    return None
