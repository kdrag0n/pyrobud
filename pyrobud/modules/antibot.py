import asyncio
from datetime import timedelta, timezone
from typing import ClassVar, Union

import telethon as tg

from .. import command, module, util

MessageEvent = Union[tg.events.NewMessage.Event, tg.events.ChatAction.Event]


class AntibotModule(module.Module):
    name: ClassVar[str] = "Antibot"
    db: util.db.AsyncDB
    group_db: util.db.AsyncDB
    user_db: util.db.AsyncDB

    suspicious_keywords = [
        "investment",
        "profit",
        "binance",
        "binanse",
        "bitcoin",
        "testnet",
        "bitmex",
        "wealth",
        "mytoken",
        "no scam",
        "legit",
        "trading",
        "binary option",
        "talk with you in private",
        "go_start",
        "s.tart",
        "cash out",
    ]

    suspicious_entities = [
        tg.tl.types.MessageEntityUrl,
        tg.tl.types.MessageEntityTextUrl,
        tg.tl.types.MessageEntityEmail,
        tg.tl.types.MessageEntityPhone,
        tg.tl.types.MessageEntityCashtag,
    ]

    async def on_load(self) -> None:
        self.db = self.bot.get_db("antibot")
        self.group_db = self.db.prefixed_db("groups.")
        self.user_db = self.db.prefixed_db("users.")

        # Migrate message tracking start times to the new per-group format
        fmsg_start_time = await self.db.get("first_msg_start_time")
        if fmsg_start_time is not None:
            self.log.info("Migrating message tracking start times to the new per-group format")

            async for key, value in self.group_db:
                if key.endswith(".enabled") and value:
                    await self.group_db.put(key.replace(".enabled", ".enable_time"), fmsg_start_time)

            await self.db.delete("first_msg_start_time")

    def msg_has_suspicious_entity(self, msg: tg.custom.Message) -> bool:
        if not msg.entities:
            return False

        # Messages containing certain entities are more likely to be spam
        return any(type(entity) in type(self).suspicious_entities for entity in msg.entities)

    def msg_has_suspicious_keyword(self, msg: tg.custom.Message) -> bool:
        if not msg.raw_text:
            return False

        # Many spam messages mention certain keywords, such as cryptocurrency exchanges
        l_text = msg.raw_text.lower()
        return any(kw in l_text for kw in type(self).suspicious_keywords)

    def msg_content_suspicious(self, msg: tg.custom.Message) -> bool:
        # Consolidate message content checks
        return self.msg_has_suspicious_entity(msg) or self.msg_has_suspicious_keyword(msg)

    @staticmethod
    def msg_type_suspicious(msg: tg.custom.Message) -> bool:
        return bool(msg.contact or msg.geo or msg.game)

    async def msg_data_is_suspicious(self, msg: tg.custom.Message) -> bool:
        incoming = not msg.out
        has_date = msg.date
        forwarded = msg.forward

        # Message *could* be suspicious if we didn't send it
        # Check for a date to exonerate empty messages
        if incoming and has_date:
            # Lazily evaluate suspicious content as it is more expensive
            if forwarded:
                # Messages forwarded from a linked channel by Telegram don't have a sender
                # We can assume these messages are safe since only admins can link channels
                sender = await msg.get_sender()
                if sender is None:
                    return False

                # Spambots don't forward their own messages; they mass-forward
                # messages from central coordinated channels for maximum efficiency
                # This protects users who forward questions with links/images to
                # various support chats asking for help (arguably, that's spammy,
                # it's out of the scope of this function)
                if msg.forward.from_id == sender.id or msg.forward.from_name == tg.utils.get_display_name(sender):
                    return False

                # Screen forwarded messages more aggressively
                return msg.photo or self.msg_type_suspicious(msg) or self.msg_content_suspicious(msg)
            else:
                # Skip suspicious entity/photo check for non-forwarded messages
                return self.msg_type_suspicious(msg) or self.msg_has_suspicious_keyword(msg)

        return False

    async def msg_is_suspicious(self, msg: tg.custom.Message) -> bool:
        # Check if the data in the message is suspicious
        if not await self.msg_data_is_suspicious(msg):
            return False

        # Load message metadata entities
        chat = await msg.get_chat()
        sender = await msg.get_sender()

        # Messages forwarded from a linked channel by Telegram don't have a sender
        # We can assume these messages are safe since only admins can link channels
        if sender is None:
            return False

        # Load group-specific user information
        try:
            ch_participant = await self.bot.client(tg.tl.functions.channels.GetParticipantRequest(chat, sender))
        except (ValueError, tg.errors.UserNotParticipantError):
            # User was already banned or deleted; we don't need to proceed
            return False

        participant = ch_participant.participant

        # Exempt the group creator
        if isinstance(participant, tg.tl.types.ChannelParticipantCreator):
            return False

        delta = msg.date - participant.date
        if delta.total_seconds() <= await self.db.get("threshold_time", 30):
            # Suspicious message was sent shortly after joining
            return True

        join_time_sec = int(participant.date.replace(tzinfo=timezone.utc).timestamp())
        if join_time_sec > await self.group_db.get(f"{msg.chat_id}.enable_time", 0):
            # We started tracking first messages in this group before the user
            # joined, so we can run the first message check
            if not await self.user_db.get(f"{sender.id}.has_spoken_in_{msg.chat_id}", False):
                # Suspicious message was the user's first message in this group
                return True

        # Allow this message
        return False

    @staticmethod
    def profile_check_invite(user: tg.types.User) -> bool:
        # Some spammers have Telegram invite links in their first or last names
        return "t.me/" in tg.utils.get_display_name(user)

    async def user_is_suspicious(self, user: tg.types.User) -> bool:
        # Some spammers have invites in their names
        return self.profile_check_invite(user)

    async def take_action(self, event: MessageEvent, user: tg.types.User) -> None:
        # Wait a bit for welcome bots to react
        await asyncio.sleep(1)

        # Delete all of the sender's messages
        chat = await event.get_chat()
        request = tg.tl.functions.channels.DeleteUserHistoryRequest(chat, user)
        await self.bot.client(request)

        # Kick the sender
        await self.bot.client.kick_participant(chat, user)

        # Log the event
        self.log.info(f'Kicked spambot with ID {user.id} in group "{chat.title}"')
        await event.reply(
            f"❯❯ **Kicked auto-detected spambot** with ID `{user.id}`", schedule=timedelta(seconds=10),
        )
        await self.bot.dispatch_event("stat_event", "spambots_banned", wait=False)

        # Delete the spam message just in case
        await event.delete()

    async def is_enabled(self, event: MessageEvent) -> bool:
        return bool(event.is_group and await self.group_db.get(f"{event.chat_id}.enabled", False))

    async def on_message(self, msg: tg.events.NewMessage.Event) -> None:
        # Only run in groups where antibot is enabled
        if await self.is_enabled(msg):
            if await self.msg_is_suspicious(msg.message):
                # This is most likely a spambot, take action against the user
                user = await msg.get_sender()
                await self.take_action(msg, user)
            else:
                await self.user_db.put(f"{msg.sender_id}.has_spoken_in_{msg.chat_id}", True)

    async def clear_group(self, group_id: int) -> None:
        async for key, _ in self.group_db.iterator(prefix=f"{group_id}."):
            await self.group_db.delete(key)

        async for key, _ in self.user_db:
            if key.endswith(f".has_spoken_in_{group_id}"):
                await self.user_db.delete(key)

    async def on_chat_action(self, action: tg.events.ChatAction.Event) -> None:
        # Remove has-spoken-in flag for departing users
        if action.user_left and await self.is_enabled(action):
            await self.user_db.delete(f"{action.user_id}.has_spoken_in_{action.chat_id}")

            # Clean up antibot data if we left the group
            if action.user_id == self.bot.uid:
                self.log.info(f"Cleaning up settings for group {action.chat_id}")
                await self.clear_group(action.chat_id)

            return

        # Only filter new users
        if not (action.user_added or action.user_joined):
            return

        # Only act in groups where this is enabled
        if not await self.is_enabled(action):
            return

        # Fetch the user's data and run checks
        user = await action.get_user()
        if await self.user_is_suspicious(user):
            # This is most likely a spambot, take action against the user
            await self.take_action(action, user)

    @command.desc("Toggle the antibot auto-moderation feature in this group")
    async def cmd_antibot(self, ctx: command.Context) -> str:
        if not ctx.msg.is_group:
            return "__Antibot can only be used in groups.__"

        if not ctx.msg.is_channel:
            return "__Please convert this group to a supergroup in order to enable antibot.__"

        if ctx.input:
            state = ctx.input.lower() in util.INPUT_YES
        else:
            state = not await self.group_db.get(f"{ctx.msg.chat_id}.enabled", False)

        if state:
            # Check for required permissions
            chat = await ctx.msg.get_chat()
            ch_participant = await self.bot.client(tg.tl.functions.channels.GetParticipantRequest(chat, self.bot.user))
            ptcp = ch_participant.participant

            if isinstance(ptcp, tg.types.ChannelParticipantCreator):
                # Group creator always has all permissions
                pass
            elif isinstance(ptcp, tg.types.ChannelParticipantAdmin):
                # Check for the required admin permissions
                if not (ptcp.admin_rights.delete_messages and ptcp.admin_rights.ban_users):
                    return "__Antibot requires the **Delete Messages** and **Ban Users** permissions.__"
            else:
                return "__I must be an admin with the **Delete Messages** and **Ban Users** permissions for antibot to work.__"

            await self.group_db.put(f"{ctx.msg.chat_id}.enabled", True)
            await self.group_db.put(f"{ctx.msg.chat_id}.enable_time", util.time.sec())
        else:
            await self.clear_group(ctx.msg.chat_id)

        status = "enabled" if state else "disabled"
        return f"Antibot is now **{status}** in this group."
