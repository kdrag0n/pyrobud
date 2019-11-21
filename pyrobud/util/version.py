import logging
import os
import pkg_resources
import sys

from . import git

log = logging.getLogger(__name__)


def get_commit():
    if git.have_git:
        repo = git.get_repo()
        if not repo:
            return

        # Attempt to get the current Git commit
        try:
            return repo.head.object.hexsha[:8]
        except Exception as e:
            log.warn("Error querying Git commit", exc_info=e)

    return None
