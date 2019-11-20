import os.path


def split_path(path):
    return os.path.normpath(path).lstrip(os.path.sep).split(os.path.sep)
