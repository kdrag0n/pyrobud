#!/usr/bin/env python3

from bot import Bot
import asyncio
import uvloop
import toml
import util

def main():
    config_path = 'config.toml'

    print('Loading config...')
    config = toml.load(config_path)

    print('Initializing bot...')
    bot = Bot(config, config_path)

    print('Starting bot...')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())

    bot.client.run_until_disconnected()

    print('\nStopping bot...')
    loop.run_until_complete(bot.stop())

if __name__ == '__main__':
    uvloop.install()
    main()
