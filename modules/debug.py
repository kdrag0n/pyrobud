import command
import inspect
import module
import json
import util
import yaml
import re

class DebugModule(module.Module):
    name = 'Debug'

    @command.desc('Time `1 + 1`')
    def cmd_time11(self, msg):
        reps = 1000000

        before = util.time_us()
        for _ in range(reps):
            _ = 1 + 1
        after = util.time_us()

        el_us = (after - before) / reps
        return '`1 + 1`: %.0f ns' % (el_us * 1000)

    @command.desc('Evaluate code')
    @command.alias('ev', 'c')
    def cmd_eval(self, msg, raw_args):
        before = util.time_us()
        result = eval(util.filter_input_block(raw_args))
        after = util.time_us()

        el_us = after - before
        el_str = util.format_duration_us(el_us)

        return f'''```{str(result)}```

Time: {el_str}'''

    @command.desc('Get the code of a command')
    def cmd_src(self, msg, cmd_name):
        if cmd_name is None or len(cmd_name) < 1:
            return '__Command name required to get source code.__'

        src = inspect.getsource(self.bot.commands[cmd_name].func)
        filtered_src = re.sub(r'^    ', '', src, flags=re.MULTILINE)
        return f'```{filtered_src}```\u200b'

    @command.desc('Evalulate code (statement)')
    def cmd_exec(self, msg, raw_args):
        exec(util.filter_input_block(raw_args))
        return 'Evaulated.'

    @command.desc('Get plain text of a message')
    @command.alias('text')
    def cmd_gtx(self, msg):
        if not msg.reply_to_message:
            return '__Reply to a message to get the text of.__'

        return f'```{msg.reply_to_message.text}```'

    @command.desc('Send text')
    def cmd_echo(self, msg, text):
        if not text:
            return '__Provide text to send.__'

        return text

    @command.desc('Dump all the data of a message')
    @command.alias('md', 'msginfo', 'minfo')
    def cmd_mdump(self, msg):
        if not msg.reply_to_message:
            return '__Reply to a message to get its data.__'

        j = str(msg.reply_to_message)
        dat = json.loads(j)

        def _filter(obj):
            if '_' in obj:
                del obj['_']
            if 'phone_number' in obj:
                del obj['phone_number']

            for item in obj.values():
                if isinstance(item, dict):
                    _filter(item)

        _filter(dat)

        yml = yaml.dump(dat, default_flow_style=False)

        return f'```{yml}```\u200b'

    @command.desc('Save the config')
    @command.alias('sc')
    def cmd_save_config(self, msg):
        self.bot.save_config()
        return 'Config saved to disk.'

    @command.desc('Send media by file ID')
    @command.alias('file')
    def cmd_fileid(self, msg, file_id):
        if not file_id and not msg.reply_to_message:
            return '__Provide a file ID to send or reply to a message with media to get its ID.__'

        if file_id:
            reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None

            self.bot.mresult(msg, 'Sending media...')
            self.bot.client.send_cached_media(msg.chat.id, file_id, reply_to_message_id=reply_id)
            self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)
        else:
            rep = msg.reply_to_message
            if not rep.media:
                return '__Provide a file ID to send or reply to a message with media to get its ID.__'

            for typ in util.media_types:
                obj = getattr(rep, typ)
                if obj:
                    if typ == 'photo':
                        fid = obj.sizes[-1].file_id
                    else:
                        fid = obj.file_id

                    return f'File ID: `{fid}`'

            return '__No compatible media found.__'

    @command.desc('Get all contextually relevant IDs')
    def cmd_id(self, msg):
        lines = []

        reply = msg.reply_to_message
        if reply:
            lines.append(f"Message ID: `{reply.message_id}`")

            if reply.from_user:
                lines.append(f"Message author ID: `{reply.from_user.id}`")

            if reply.forward_from:
                lines.append(f"Forwarded message author ID: `{reply.forward_from.id}`")

            if reply.forward_from_chat:
                lines.append(f"Forwarded message chat ID: `{reply.forward_from_chat.id}`")

            if reply.forward_from_message_id:
                lines.append(f"Forwarded message's original ID: `{reply.forward_from_message_id}`")

        if msg.chat:
            typ = 'Unknown chat'
            if msg.chat.type == 'private':
                typ = 'Private chat'
            elif msg.chat.type == 'group' or msg.chat.type == 'supergroup':
                typ = 'Group'
            elif msg.chat.type == 'channel':
                typ = 'Channel'

            lines.append(f'{typ} ID: `{msg.chat.id}`')

        lines.append(f"My user ID: `{self.bot.uid}`")

        return '\n'.join(lines)
