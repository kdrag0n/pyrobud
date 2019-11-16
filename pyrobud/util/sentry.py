import sentry_sdk

from . import version
from .. import __version__

PUBLIC_CLIENT_KEY = "https://75fe67fda0594284b2c3aea6b90a1ba7@sentry.io/1817585"


def init():
    # Use Git commit if possible, otherwise fall back to the version number
    release = version.get_commit()
    if release is None:
        release = __version__

    # Initialize the Sentry SDK using the public client key
    sentry_sdk.init(PUBLIC_CLIENT_KEY, release=release)
