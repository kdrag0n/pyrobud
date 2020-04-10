import argparse
import logging

from . import DEFAULT_CONFIG_PATH, __description__, launch, logs

parser = argparse.ArgumentParser(description=__description__)
parser.add_argument(
    "-c",
    "--config-path",
    metavar="PATH",
    type=str,
    default=DEFAULT_CONFIG_PATH,
    help="config file to use",
)

args = parser.parse_args()

log = logging.getLogger("launch")
logs.setup_logging()

log.info("Loading code...")


def main():
    """Main entry point for the default bot command."""

    launch.main(config_path=args.config_path)


if __name__ == "__main__":
    main()
