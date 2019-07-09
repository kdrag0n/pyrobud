import aiohttp
import asyncio
import command
import module
import util
import os

class NetworkModule(module.Module):
    name = 'Network'

    @command.desc('Pong')
    async def cmd_ping(self, msg):
        before = util.time_ms()
        await msg.result('Calculating response time...')
        after = util.time_ms()

        return 'Request response time: %d ms' % (after - before)

    async def get_text_input(self, msg, input_arg):
        if msg.is_reply:
            reply_msg = await msg.get_reply_message()

            if reply_msg.document:
                text = await util.msg_download_file(reply_msg, msg)
            elif reply_msg.text:
                text = reply_msg.text
            else:
                return ('error', '__Reply to a message with text or a text file, or provide text in command.__')
        else:
            if input_arg:
                text = util.filter_code_block(input_arg).encode()
            else:
                return ('error', '__Reply to a message or provide text in command.__')

        return ('success', text)

    @command.desc('Paste message text to Hastebin')
    @command.alias('hs')
    async def cmd_haste(self, msg, input_text):
        status, text = await self.get_text_input(msg, input_text)
        if status == 'error':
            return text

        await msg.result('Uploading text to [Hastebin](https://hastebin.com/)...')

        async with self.bot.http_session.post('https://hastebin.com/documents', data=text) as resp:
            resp_data = await resp.json()
            return f'https://hastebin.com/{resp_data["key"]}'

    @command.desc('Paste message text to Dogbin')
    async def cmd_dog(self, msg, input_text):
        status, text = await self.get_text_input(msg, input_text)
        if status == 'error':
            return text

        await msg.result('Uploading text to [Dogbin](https://del.dog/)...')

        async with self.bot.http_session.post('https://del.dog/documents', data=text) as resp:
            resp_data = await resp.json()
            return f'https://del.dog/{resp_data["key"]}'

    @command.desc('Upload given file to file.io')
    async def cmd_fileio(self, msg, expires):
        if not msg.is_reply:
            return '__Reply to a file to upload it.__'

        if expires == 'help':
            return '__Expiry format: 1y/12m/52w/365d__'
        elif expires:
            if expires[-1] not in ['y', 'm', 'w', 'd']:
                return '__Unknown unit. Expiry format: 1y/12m/52w/365d__'
            else:
                try:
                    int(expires[:-1])
                except ValueError:
                    return '__Invalid number. Expiry format: 1y/12m/52w/365d__'
        else:
            expires = '2d'

        reply_msg = await msg.get_reply_message()
        if not reply_msg.document:
            return "__That message doesn't contain a file.__"

        data = await util.msg_download_file(reply_msg, msg)

        await msg.result('Uploading file to [file.io](https://file.io/)...')

        async with self.bot.http_session.post(f'https://file.io/?expires={expires}', data={'file': data}) as resp:
            resp_data = await resp.json()

            if not resp_data['success']:
                return f'__Error uploading file — status code {resp.status}__'

            return resp_data['link']

    @command.desc('Upload given file to transfer.sh')
    async def cmd_transfer(self, msg):
        if not msg.is_reply:
            return '__Reply to a file to upload it.__'

        reply_msg = await msg.get_reply_message()
        if not reply_msg.document:
            return "__That message doesn't contain a file.__"

        data = await util.msg_download_file(reply_msg, msg)

        await msg.result('Uploading file to [transfer.sh](https://transfer.sh/)...')

        filename = reply_msg.file.name
        async with self.bot.http_session.put(f'https://transfer.sh/{filename}', data=data) as resp:
            if resp.status != 200:
                return f'__Error uploading file — status code {resp.status}__'

            return await resp.text()
