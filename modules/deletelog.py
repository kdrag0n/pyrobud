from datetime import datetime, timedelta
import telethon as tg, command, module, re, asyncio, util, sqlite3


class DeleteLog(module.Module):
    name = "Deleted Logger"
    enabled = False

    queue = list()
    db: sqlite3.Connection

    async def on_load(self):
        self.db = sqlite3.connect('messages.sqlitedb', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    async def on_message(self, msg: tg.custom.Message):
        if not self.enabled: return
        self.db.execute(f'CREATE TABLE IF NOT EXISTS "{msg.chat_id}" ("content" TEXT, "author" NUMERIC, "created" TIMESTAMP);')
        self.db.execute('INSERT INTO "' + str(msg.chat_id) + '" ("content","author","created") VALUES (%s,%s,%s);', (msg.text, msg.from_id, msg.date))

    async def on_message_deleted(self, msg: tg.events.MessageDeleted):
        if not self.enabled: return
        haschat = hasattr(msg.original_update, "channel_id")
        chat = util.ChatStr(await self.bot.client.get_input_entity(msg.original_update.channel_id)) if haschat else "an Unknown chat"
        msg_ids = '`, `'.join(str(x) for x in msg.deleted_ids)
        await self.bot.client.send_message("Deleted Messages", f"Someone deleted {len(msg.deleted_ids)} message(s) from {chat}\nMessages: `{msg_ids}`")
        """
        self.queue.append(msg.stringify())
        if len(self.queue) > 9:
            msgs = util.splitMsg('\n'.join(self.queue))
            for msg in msgs: await self.bot.client.send_message("Deleted Messages", msg)
            self.queue.clear()
        """