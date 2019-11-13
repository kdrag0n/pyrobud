import git
import sentry_sdk

PUBLIC_CLIENT_KEY = "https://75fe67fda0594284b2c3aea6b90a1ba7@sentry.io/1817585"


def init():
    # Attempt to get the current Git commit
    try:
        repo = git.Repo(search_parent_directories=True)
        release = repo.head.object.hexsha[:8]
    # Silence a bogus pylint error
    # pylint: disable=no-member
    except git.exc.InvalidGitRepositoryError:
        release = None

    # Initialize the Sentry SDK using the public client key
    sentry_sdk.init(PUBLIC_CLIENT_KEY, release=release)
