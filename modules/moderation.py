from datetime import datetime

import telethon as tg

import command
import module
import util


class ModerationModule(module.Module):
    name = "Moderation"

    @command.desc("Mention everyone in this group (**DO NOT ABUSE**)")
    @command.alias("evo", "@everyone")
    async def cmd_everyone(self, msg, comment, *, tag="\U000e0020everyone", filter=None):
        if not msg.is_group:
            return "__This command can only be used in groups.__"

        mention_text = f"@{tag}"
        if comment:
            mention_text += " " + comment

        mention_slots = 4096 - len(mention_text)

        chat = await msg.get_chat()
        async for user in self.bot.client.iter_participants(chat, filter=filter):
            mention_text += f"[\u200b](tg://user?id={user.id})"

            mention_slots -= 1
            if mention_slots == 0:
                break

        await msg.respond(mention_text, reply_to=msg.reply_to_msg_id)
        await msg.delete()

    @command.desc("Mention all admins in a group (**DO NOT ABUSE**)")
    @command.alias("adm", "@admin")
    async def cmd_admin(self, msg, comment):
        await self.cmd_everyone(msg, comment, tag="admin", filter=tg.tl.types.ChannelParticipantsAdmins)

    @command.desc("Ban users from all chats where you have permissions to do so")
    @command.alias("gban")
    async def cmd_globalban(self, msg : tg.events.newmessage, *users : tuple):
        users = list(map(int, users))
        if msg.is_reply:
            replied_msg = await msg.get_reply_message()
            users.append(replied_msg.from_id)
        users = list(set(users))
        chatcount = 0; users_to_ban = []
        for userid in users:
            user = await self.bot.client.get_entity(userid)
            users_to_ban.append(user)
        async for dialog in self.bot.client.iter_dialogs():
            if not dialog.is_group or not dialog.is_channel: continue
            chat = await msg.get_entity(dialog.id)
            async for user in self.bot.client.iter_participants(chat, filter=tg.tl.types.ChannelParticipantsAdmins):
                if user.id == self.bot.uid:
                    await self.banUsers(users_to_ban, chat)
                    chatcount += 1
                    break
        return f"{len(users_to_ban)} users have been banned from {chatcount} chats!"


    @command.desc("Ban users from the current channel")
    async def cmd_ban(self, msg : tg.events.newmessage, *input_userids : tuple):
        userids = list(map(int, input_userids))
        if msg.is_reply:
            replied_msg = await msg.get_reply_message()
            userids.append(replied_msg.from_id)
        chat = await msg.get_chat()
        reply = await self.banUserIDs(userids, chat)
        await msg.respond(reply, reply_to=msg.reply_to_msg_id)
        await msg.delete()

    async def banUserIDs(self, userids, chat):
        userids = list(set(userids))
        reply = f"{len(userids)} users have been banned from {chat.title}!\n"
        for userid in userids:
            user = await self.bot.client.get_entity(userid)
            reply += "\n" + util.UserStr(user)
            await self.banUser(user, chat)
        return reply

    async def banUsers(self, users, chat):
        for user in users:
            await self.banUser(user, chat)

    async def banUser(self, user, chat):
        rights = tg.tl.types.ChatBannedRights(until_date=None, view_messages=True)
        ban_request = tg.tl.functions.channels.EditBannedRequest(chat, user, rights)
        await self.bot.client(ban_request)

    @command.desc("Ban users from the current chat by ID")
    async def cmd_ban(self, msg, *input_ids):
        try:
            # Parse user IDs without duplicates
            user_ids = list(dict.fromkeys(map(int, input_ids)))
        except ValueError:
            return ""

        if msg.is_reply:
            reply_msg = await msg.get_reply_message()
            user_ids.append(reply_msg.from_id)

        chat = await msg.get_chat()
        lines = [f"Banned {len(user_ids)} users:"]
        await msg.result(f"Banning {len(user_ids)} users...")

        for user_id in user_ids:
            user = await self.bot.client.get_entity(user_id)
            lines.append(f"    \u2022 {util.mention_user(user)} (`{user_id}`)")

            rights = tg.tl.types.ChatBannedRights(until_date=None, view_messages=True)
            ban_request = tg.tl.functions.channels.EditBannedRequest(chat, user, rights)
            await self.bot.client(ban_request)

        return "\n".join(lines)

    @command.desc("Purge specified amount or all messages in the current chat")
    @command.alias("prunemessages", "purgemsgs", "prunemsgs")
    async def cmd_purgemessages(self, msg: tg.events.newmessage): # , amount: int = None
        await self.bot.client.delete_messages(msg.chat_id, [x for x in range(msg.id)])
        await msg.result(f"Purged last {msg.id} messages!")

    @command.desc("Prune deleted members in this group or the specified group")
    @command.alias("purgemembers")
    async def cmd_prunemembers(self, msg, chat):
        incl_chat_name = bool(chat)
        if chat:
            chat = await self.bot.client.get_entity(chat)
        else:
            chat = await msg.get_chat()

        if incl_chat_name:
            _chat_name = f" from **{chat.title}**"
            _chat_name2 = f" in **{chat.title}**"
        else:
            _chat_name = ""
            _chat_name2 = ""

        await msg.result(f"Fetching members{_chat_name}...")
        all_members = await self.bot.client.get_participants(chat)

        last_time = datetime.now()
        total_count = len(all_members)
        pruned_count = 0
        idx = 0

        status_text = f"Pruning deleted members{_chat_name}..."
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
                await msg.result(
                    f"{status_text} {percent_done}% done ({idx + 1} of {total_count} processed; {pruned_count} banned)"
                )

            last_time = now
            idx += 1

        percent_pruned = int(pruned_count / total_count * 100)
        await msg.result(
            f"Pruned {pruned_count} deleted users{_chat_name2} — {percent_pruned}% of the original member count."
        )
