from datetime import datetime
from typing import ClassVar, List, Optional

import telethon as tg

from .. import command, module, util


class ModerationModule(module.Module):
    name: ClassVar[str] = "Moderation"

    @command.desc("Mention everyone in this group (**DO NOT ABUSE**)")
    @command.usage("[comment?]", optional=True)
    @command.alias("evo", "@everyone")
    async def cmd_everyone(
        self,
        ctx: command.Context,
        *,
        tag: str = "\U000e0020everyone",
        user_filter: Optional[tg.types.TypeChannelParticipantsFilter] = None,
    ) -> Optional[str]:
        comment = ctx.input

        if not ctx.msg.is_group:
            return "__This command can only be used in groups.__"

        mention_text = f"@{tag}"
        if comment:
            mention_text += " " + comment

        mention_slots = 4096 - len(mention_text)

        chat = await ctx.msg.get_chat()
        async for user in self.bot.client.iter_participants(chat, filter=user_filter):
            mention_text += f"[\u200b](tg://user?id={user.id})"

            mention_slots -= 1
            if mention_slots == 0:
                break

        await ctx.respond(mention_text, mode="repost")
        return None

    @command.desc("Mention all admins in a group (**DO NOT ABUSE**)")
    @command.usage("[comment?]", optional=True)
    @command.alias("adm", "@admin")
    async def cmd_admin(self, ctx: command.Context) -> Optional[str]:
        return await self.cmd_everyone(
            ctx, tag="admin", user_filter=tg.tl.types.ChannelParticipantsAdmins
        )

    @command.desc("Ban user(s) from the current chat by ID or reply")
    @command.usage(
        "[ID(s) of the user(s) to ban?, or reply to user's message]", optional=True
    )
    async def cmd_ban(self, ctx: command.Context) -> str:
        input_ids = ctx.args

        try:
            # Parse user IDs without duplicates
            user_ids = list(dict.fromkeys(map(int, input_ids)))
        except ValueError:
            return "__Encountered invalid ID while parsing arguments.__"

        if ctx.msg.is_reply:
            reply_msg = await ctx.msg.get_reply_message()
            user_ids.append(reply_msg.from_id)

        if not user_ids:
            return "__Provide a list of user IDs to ban, or reply to a user's message to ban them.__"

        lines: List[str]
        chat = await ctx.msg.get_chat()
        single_user = len(user_ids) == 1
        if single_user:
            lines = []
        else:
            lines = [f"**Banned {len(user_ids)} users:**"]
            await ctx.respond(f"Banning {len(user_ids)} users...")

        for user_id in user_ids:
            try:
                user = await self.bot.client.get_entity(user_id)
            except ValueError:
                if single_user:
                    lines.append(f"__Unable to find user__ `{user_id}`.")
                else:
                    lines.append(f"Unable to find user `{user_id}`")

                continue

            if not isinstance(user, tg.types.User):
                ent_type = type(user).__name__.lower()
                lines.append(f"Skipped {ent_type} object (`{user_id}`)")
                continue

            user_spec = f"{util.tg.mention_user(user)} (`{user_id}`)"
            if single_user:
                lines.append(f"**Banned** {user_spec}")
            else:
                lines.append(user_spec)

            rights = tg.tl.types.ChatBannedRights(until_date=None, view_messages=True)
            ban_request = tg.tl.functions.channels.EditBannedRequest(chat, user, rights)

            try:
                await self.bot.client(ban_request)
            except tg.errors.ChatAdminRequiredError:
                return "__I need permission to ban users in this chat.__"

        return util.text.join_list(lines)

    @command.desc("Prune deleted members in this group or the specified group")
    @command.usage("[target chat ID/username/...?]", optional=True)
    async def cmd_prune(self, ctx: command.Context) -> str:
        if ctx.input:
            chat = await self.bot.client.get_entity(ctx.input)
            if isinstance(chat, tg.types.User):
                return f"`{ctx.input}` __references a user, not a chat.__"

            _chat_name = f" from **{chat.title}**"
            _chat_name2 = f" in **{chat.title}**"
        else:
            chat = await ctx.msg.get_chat()
            _chat_name = ""
            _chat_name2 = ""

        await ctx.respond(f"Fetching members{_chat_name}...")
        all_members = await self.bot.client.get_participants(chat)

        last_time = datetime.now()
        total_count = len(all_members)
        pruned_count = 0
        idx = 0

        status_text = f"Pruning deleted members{_chat_name}..."
        await ctx.respond(status_text)

        for user in all_members:
            if user.deleted:
                ban_request: tg.tl.TLRequest
                if isinstance(chat, tg.types.Chat):
                    ban_request = tg.tl.functions.messages.DeleteChatUserRequest(
                        chat.id, user
                    )
                else:
                    rights = tg.tl.types.ChatBannedRights(
                        until_date=None, view_messages=True
                    )
                    ban_request = tg.tl.functions.channels.EditBannedRequest(
                        chat, user, rights
                    )

                await self.bot.client(ban_request)
                pruned_count += 1

            percent_done = int((idx + 1) / total_count * 100)
            now = datetime.now()
            delta = now - last_time
            if delta.total_seconds() >= 0.25:
                await ctx.respond(
                    f"{status_text} {percent_done}% done ({idx + 1} of {total_count} processed; {pruned_count} banned)"
                )

            last_time = now
            idx += 1

        percent_pruned = int(pruned_count / total_count * 100)
        return f"Pruned {pruned_count} deleted users{_chat_name2} — {percent_pruned}% of the original member count."
