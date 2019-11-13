import module, util
import telethon as tg
import re
import asyncio
from datetime import timedelta, datetime, timezone
from telethon.tl.types import PeerUser, PeerChannel


class AutoAdminModule(module.Module):
    name = "Auto Admin"

    no_events = [
        "UpdateNewChannelMessage", "UpdateMessageID", "UpdateReadChannelInbox", "UpdateReadChannelOutbox",
        "UpdateEditChannelMessage", "UpdateUserStatus"
    ]

    async def on_raw_event(self, event):
        name = event.__class__.__name__
        if name == "UpdateChatParticipants":
            print(event.toString())
            if event.participants.version == 1:
                is_creator = False
                for participant in event.participants.participants:
                    participant_type = participant.__class__.__name__
                    if participant_type == "ChatParticipantCreator":
                        if participant.user_id == self.bot.uid: is_creator = True
                    # elif == "ChatParticipant":
                if is_creator:
                    await asyncio.sleep(2.5)
                    chat = await self.bot.client.get_entity(event.participants.chat_id)
                    await self.bot.client(
                        tg.tl.functions.channels.InviteToChannelRequest(chat, self.bot.config["bot"]["auto_admins"]))
                    rights = tg.tl.types.ChatAdminRights(post_messages=True, add_admins=True, invite_users=True,
                                                         change_info=True,
                                                         ban_users=True, delete_messages=True, pin_messages=True,
                                                         invite_link=True, edit_messages=True)
                    for auto_admin in self.bot.config["bot"]["auto_admins"]:
                        user = await self.bot.client.get_entity(auto_admin)
                        await self.bot.client(tg.tl.functions.channels.EditAdminRequest(chat, user, rights))
                    admincnt = len(self.bot.config["bot"]["auto_admins"])
                    chat.send_message(f"Added {admincnt} admins.")