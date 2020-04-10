import logging
from typing import Optional

from . import git

log = logging.getLogger(__name__)


def get_commit() -> Optional[str]:
    """Returns the current Git commit hash, if available."""

    if git.have_git:
        repo = git.get_repo()
        if not repo:
            return None

        # Attempt to get the current Git commit
        try:
            return repo.head.object.hexsha[:8]
        except Exception as e:
            log.warning("Error querying Git commit", exc_info=e)

    return None
