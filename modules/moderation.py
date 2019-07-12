import telethon as tg

import command
import module


class ModerationModule(module.Module):
    name = 'Moderation'

    @command.desc('Mention everyone in this group (**DO NOT ABUSE**)')
    @command.alias('evo', '@everyone')
    async def cmd_everyone(self, msg, comment, *, tag='\U000e0020everyone', filter=None):
        if not msg.is_group:
            return '__This command can only be used in groups.__'

        mention_text = f'@{tag}'
        if comment:
            mention_text += ' ' + comment

        mention_slots = 4096 - len(mention_text)

        chat = await msg.get_chat()
        async for user in self.bot.client.iter_participants(chat, filter=filter):
            mention_text += f'[\u200b](tg://user?id={user.id})'

            mention_slots -= 1
            if mention_slots == 0:
                break

        await msg.respond(mention_text, reply_to=msg.reply_to_msg_id)
        await msg.delete()

    @command.desc('Mention all admins in a group (**DO NOT ABUSE**)')
    @command.alias('adm', '@admin')
    async def cmd_admin(self, msg, comment):
        await self.cmd_everyone(msg, comment, tag='admin', filter=tg.tl.types.ChannelParticipantsAdmins)
