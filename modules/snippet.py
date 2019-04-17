import command
import module
import re

class SnippetModule(module.Module):
    name = 'Snippet'

    def on_load(self):
        if 'snippets' not in self.bot.config:
            self.bot.config['snippets'] = {}
            print('Initialized snippet table in config')

    def snip_repl(self, m):
        if m.group(1) in self.bot.config['snippets']:
            self.log_stat('replaced')
            return self.bot.config['snippets'][m.group(1)]

        return m.group(0)

    def on_message(self, msg):
        if msg.from_user and msg.from_user.id == self.bot.uid:
            if msg.text:
                orig_txt = msg.text.markdown
                txt = msg.text.markdown

                txt = re.sub(r'/([^ ]+?)/', self.snip_repl, orig_txt)

                if txt != orig_txt:
                    self.bot.mresult(msg, txt)

    @command.desc('Save a snippet (fetch: `/snippet/`)')
    def cmd_snip(self, msg, *args):
        if not args:
            return '__Specify a name for the snippet, then reply to a message or provide text.__'

        if msg.reply_to_message:
            content = msg.reply_to_message.text.markdown
            if not content:
                if len(args) > 1:
                    content = ' '.join(args[1:])
                else:
                    return '__Reply to a message with text or provide text after snippet name.__'
        else:
            if len(args) > 1:
                content = ' '.join(args[1:])
            else:
                return '__Reply to a message with text or provide text after snippet name.__'

        name = args[0]
        if name in self.bot.config['snippets']:
            return f'__Snippet \'{name}\' already exists!__'

        self.bot.config['snippets'][name] = content.strip()

        # Actually save it to disk
        self.bot.save_config()

        return f'Snippet saved as `{name}`.'

    @command.desc('Show all snippets')
    @command.alias('sl', 'snl', 'spl')
    def cmd_sniplist(self, msg):
        if not self.bot.config['snippets']:
            return '__No snippets saved.__'

        out = 'Snippet list:'

        for name in self.bot.config['snippets'].keys():
            out += f'\n    \u2022 **{name}**'

        return out

    @command.desc('Delete a snippet')
    @command.alias('ds', 'sd', 'snd', 'spd', 'rms', 'srm', 'rs', 'sr')
    def cmd_snipdel(self, msg, name):
        if not name: return '__Provide the name of a snippet to delete.__'

        del self.bot.config['snippets'][name]
        self.bot.save_config()

        return f'Snippet `{name}` deleted.'
