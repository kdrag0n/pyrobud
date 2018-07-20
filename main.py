#!/usr/bin/env python3

from typing import Dict, Union
import bot
import toml


def main():
    config: Dict[str, Dict[str, Union[int, str]]] = toml.load('config.toml')

    inst = bot.Bot()
    inst.setup('main', config['bot']['prefix'], id=config['telegram']
               ['api_id'], hash=config['telegram']['api_hash'])
    inst.start()


if __name__ == '__main__':
    main()
