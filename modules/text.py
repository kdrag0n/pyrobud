import command
import module
import random

class TextModule(module.Module):
    name = 'Text'

    @command.desc('Unicode character from hex codepoint')
    @command.alias('cp', 'chr', 'uc')
    async def cmd_uni(self, msg, codepoint):
        if not codepoint:
            return '__Hex codepoint required.__'

        return chr(int(codepoint, 16))

    @command.desc('Get a character equivalent to a zero-width space that works on Telegram')
    @command.alias('empty')
    async def cmd_zwsp(self, msg):
        return '\U000e0020'

    @command.desc('Apply a sarcasm/mocking filter to the given text')
    @command.alias('sar', 'sarc', 'scm', 'mock')
    async def cmd_sarcasm(self, msg, text):
        if not text:
            return '__Text required.__'

        chars = list(text)
        for idx, ch in enumerate(chars):
            if random.choice((True, False)):
                ch = ch.upper()

            chars[idx] = ch

        return ''.join(chars)

    @command.desc('Apply strike-through formatting to the given text')
    @command.alias('str', 'strikethrough')
    async def cmd_strike(self, msg, text):
        if not text:
            return '__Text required.__'

        return '\u0336'.join(text) + '\u0336'

    @command.desc('Mention everyone in this group (**DO NOT ABUSE**)')
    @command.alias('evo', '@everyone')
    async def cmd_everyone(self, msg, comment):
        if not msg.is_group:
            return '__This command can only be used in groups.__'

        mention_text = '@\U000e0020everyone'
        if comment:
            mention_text += ' ' + comment

        mention_slots = 4096 - len(mention_text)

        chat = await msg.get_chat()
        async for user in self.bot.client.iter_participants(chat):
            mention_text += f'[\u200b](tg://user?id={user.id})'
            mention_slots -= 1

        await msg.respond(mention_text, reply_to=msg.reply_to_msg_id)
        await msg.delete()
