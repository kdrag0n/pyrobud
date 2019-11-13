import telethon as tg, command, module, re, asyncio
from datetime import datetime, timedelta
from random import choice


class Bluscream(module.Module):
    name = "Bluscream"
    funcs = [str.lower, str.upper]
    prefixes = ["Hallo", "Hi", "Hey", "Was geht?", "Yo"]
    suffixes = ["", ":3", ":D", "<3", "♥", "👌", "✌"]
    last_deleted_media = datetime.min
    async def on_message(self, msg: tg.custom.Message):
        if msg.from_id is not None and msg.from_id == 339959826:
            if (msg.media is not None):
                await msg.delete()
                _now = datetime.now()
                if self.last_deleted_media < _now-timedelta(minutes=10):
                    await msg.reply("`Media deleted. Please don't send media directly here.`")
                    self.last_deleted_media = _now
            elif msg.text.startswith("⬆️"):
                await asyncio.sleep(10)
                await msg.reply("/newchat")
            elif msg.text.startswith("Du wurdest mit einem anderen User gematcht."):
                await asyncio.sleep(1)
                await msg.reply(choice(self.prefixes)+" "+choice(self.suffixes))

    async def on_message_edit(self, event: tg.events.MessageEdited.Event):
        if event.chat_id == 339959826 and event.message.from_id is not None and event.message.from_id == self.bot.uid:
            await event.message.reply("/revoke")
            await event.message.respond(event.message.text)

    async def cmd_bluscream(self, msg):
        return "lol"
