from datetime import datetime

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

    @command.desc('Prune deleted members in this group or the specified group')
    async def cmd_prune(self, msg, chat):
        incl_chat_name = bool(chat)
        if chat:
            chat = await self.bot.client.get_entity(chat)
        else:
            chat = await msg.get_chat()

        if incl_chat_name:
            _chat_name = f' from **{chat.title}**'
            _chat_name2 = f' in **{chat.title}**'
        else:
            _chat_name = ''
            _chat_name2 = ''

        await msg.result(f'Fetching members{_chat_name}...')
        all_members = await self.bot.client.get_participants(chat)

        last_time = datetime.now()
        total_count = len(all_members)
        pruned_count = 0
        idx = 0

        status_text = f'Pruning deleted members{_chat_name}...'
        await msg.result(status_text)

        for user in all_members:
            if user.deleted:
                rights = tg.tl.types.ChatBannedRights(until_date=None, view_messages=True)
                ban_request = tg.tl.functions.channels.EditBannedRequest(chat, user, rights)
                await self.bot.client(ban_request)

                pruned_count += 1

            percent_done = int((idx + 1) / total_count * 100)
            now = datetime.now()
            delta = now - last_time
            if delta.total_seconds() >= 0.25:
                await msg.result(f'{status_text} {percent_done}% done ({idx + 1} of {total_count} processed; {pruned_count} banned)')

            last_time = now
            idx += 1

        percent_pruned = int(pruned_count / total_count * 100)
        await msg.result(f'Pruned {pruned_count} deleted users{_chat_name2} — {percent_pruned}% of the original member count.')
