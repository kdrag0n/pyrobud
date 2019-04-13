#!/usr/bin/env python3

import bot
import toml

def main():
    print('Loading config...')
    config: bot.Config = toml.load('config.toml')

    inst: bot.Bot = bot.Bot()
    inst.setup('main', config)
    print('Starting bot...')
    inst.start()

if __name__ == '__main__':
    main()
