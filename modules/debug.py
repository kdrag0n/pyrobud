import inspect
import json
import re

import command
import module
import util


class DebugModule(module.Module):
    name = 'Debug'

    @command.desc('Time `1 + 1`')
    async def cmd_time11(self, msg):
        reps = 1000000

        before = util.time_us()
        for _ in range(reps):
            _ = 1 + 1
        after = util.time_us()

        el_us = (after - before) / reps
        return '`1 + 1`: %.0f ns' % (el_us * 1000)

    @command.desc('Evaluate code')
    @command.alias('ev', 'c')
    async def cmd_eval(self, msg, raw_args):
        def _eval():
            nonlocal msg, raw_args, self

            def send(text):
                return self.bot.loop.create_task(msg.respond(text))

            return eval(util.filter_code_block(raw_args))

        before = util.time_us()
        result = await util.run_sync(_eval)
        after = util.time_us()

        el_us = after - before
        el_str = util.format_duration_us(el_us)

        return f'''```{str(result)}```

Time: {el_str}'''

    @command.desc('Evalulate code (statement)')
    async def cmd_exec(self, msg, raw_args):
        def _exec():
            nonlocal msg, raw_args, self

            def send(text):
                return self.bot.loop.create_task(msg.respond(text))

            exec(util.filter_code_block(raw_args))

        await util.run_sync(_exec)
        return 'Code evaulated.'

    @command.desc('Get the code of a command')
    async def cmd_src(self, msg, cmd_name):
        if cmd_name is None or len(cmd_name) < 1:
            return '__Command name required to get source code.__'
        if cmd_name not in self.bot.commands:
            return f"__Command__ `{cmd_name}` __doesn't exist.__"

        src = await util.run_sync(lambda: inspect.getsource(self.bot.commands[cmd_name].func))
        filtered_src = re.sub(r'^    ', '', src, flags=re.MULTILINE)
        return f'```{filtered_src}```'

    @command.desc('Get plain text of a message')
    @command.alias('text', 'raw')
    async def cmd_gtx(self, msg):
        if not msg.is_reply:
            return '__Reply to a message to get the text of.__'

        reply_msg = await msg.get_reply_message()
        await msg.result(reply_msg.text, parse_mode=None)

    @command.desc('Send text')
    async def cmd_echo(self, msg, text):
        if not text:
            return '__Provide text to send.__'

        return text

    @command.desc('Dump all the data of a message')
    @command.alias('md', 'msginfo', 'minfo')
    async def cmd_mdump(self, msg):
        if not msg.is_reply:
            return '__Reply to a message to get its data.__'

        reply_msg = await msg.get_reply_message()
        data = reply_msg.stringify()

        return f'```{data}```'

    @command.desc('Save the config')
    @command.alias('sc')
    async def cmd_save_config(self, msg):
        await self.bot.save_config()
        return 'Config saved to disk.'

    @command.desc('Send media by file ID')
    @command.alias('file')
    async def cmd_fileid(self, msg, file_id):
        if not file_id and not msg.is_reply:
            return '__Provide a file ID to send or reply to a message with media to get its ID.__'

        if file_id:
            reply_msg = await msg.get_reply_message() if msg.is_reply else None

            await msg.result('Sending media...')
            await msg.respond(reply_to=reply_msg, file=file_id)
            await msg.delete()
        else:
            rep = await msg.get_reply_message()
            if not rep.media:
                return '__Provide a file ID to send or reply to a message with media to get its ID.__'

            if msg.file:
                return f'File ID: `{msg.file.id}`'

            return '__No compatible media found.__'

    @command.desc('Get all contextually relevant IDs')
    async def cmd_id(self, msg):
        lines = []

        if msg.is_reply:
            reply_msg = await msg.get_reply_message()
            sender = await reply_msg.get_sender()
            lines.append(f"Message ID: `{reply_msg.id}`")

            if sender:
                lines.append(f"Message author ID: `{sender.id}`")

# TODO: update
            if reply_msg.forward:
                lines.append(f"Forwarded message author ID: `{reply_msg.forward_from.id}`")

                if reply_msg.forward_from_chat:
                    lines.append(f"Forwarded message chat ID: `{reply_msg.forward_from_chat.id}`")

                if reply_msg.forward_from_message_id:
                    lines.append(f"Forwarded message's original ID: `{reply_msg.forward_from_message_id}`")

        if msg.chat_id:
            lines.append(f'Chat ID: `{msg.chat_id}`')

        lines.append(f"My user ID: `{self.bot.uid}`")

        return '\n'.join(lines)
