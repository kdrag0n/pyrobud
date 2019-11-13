import telethon as tg
from telethon.tl.types import ChannelParticipantsAdmins, User

import command, module, util
from datetime import timedelta


class LoggerModule(module.Module):
    name = "Logger"
    enabled = True

    async def on_load(self):
        pass

    def is_enabled(self, event):
        return True

    async def on_chat_action(self, action: tg.events.chataction.ChatAction.Event):
        if not self.enabled: return
        if action.user_id is not None and action.user_id != self.bot.uid: return
        txt = action.stringify(); notify = True
        if action.user_joined or action.user_left:
            _action = "⤵ Joined" if action.user_joined else "🔙 Left"
            txt = f"{action.action_message.date}\n{_action} {util.ChatStr(action.chat)}"
            if action.user_joined:
                admins = await self.bot.client.get_participants(action.chat, filter=ChannelParticipantsAdmins)
                _admins = len(admins)
                if _admins > 0:
                    txt += f"\n\n**Admins ({_admins}):**"
                    for admin in admins: txt += f"\n{util.UserStr(admin, True)}"
                notify = False
        await self.bot.client.send_message(self.bot.user, txt.strip(), schedule=timedelta(seconds=10) if notify else None)

    @command.desc("Toggle selflog")
    async def cmd_selflog(self, msg):
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        return f"Selflog is now **{status}**."
