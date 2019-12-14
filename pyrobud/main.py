import logging

from . import logs

log = logging.getLogger("launch")
logs.setup_logging()

log.info("Loading code...")

from . import launch


def main():
    launch.main()


if __name__ == "__main__":
    main()
