#!/usr/bin/env python3

import bot
import toml

def main():
    config: bot.Config = toml.load('config.toml')

    inst: bot.Bot = bot.Bot()
    inst.setup('main', config)
    inst.start()

if __name__ == '__main__':
    main()
