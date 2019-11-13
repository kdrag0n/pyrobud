import module, util
import re
import asyncio
from datetime import timedelta, datetime, timezone
from telethon.tl.types import PeerUser, PeerChannel


class BioLoggerModule(module.Module):
    name = "BioLogger"
    sleep = timedelta(minutes=10).total_seconds()

    async def on_ready(self):
        self.channel = await self.bot.client.get_entity(PeerChannel(1441900591))
        self.logchannel = await self.bot.client.get_entity(PeerChannel(1262543505))
        self.bot.loop.create_task(self.updateChannelLeaves())

    async def updateChannelLeaves(self):
        regex_timestamp = re.compile(r"\d{4}-\d+-\d+ \d+:\d+:\d{2}")
        format_timestamp = "%Y-%m-%d %H:%M:%S"  # 2019-10-28 02:10:04
        while True:
            await asyncio.sleep(60)
            last_timestamp = datetime.min.replace(tzinfo=timezone.utc)
            async for msg in self.bot.client.iter_messages(self.logchannel, 20):
                if msg.message is None: continue
                match = regex_timestamp.search(msg.message)
                if not match: continue
                last_timestamp = datetime.strptime(match.group(0), format_timestamp).replace(tzinfo=timezone.utc)
                break
            events = list()
            async for event in self.bot.client.iter_admin_log(self.channel, leave=True):
                events.append(event)
            events.reverse()
            for event in events:
                etype = ""
                if event.left:
                    etype = "🔙 Left"
                elif event.joined:
                    etype = "⤵️ Joined"
                elif event.joined_invite:
                    etype = "🔗 Joined via Invite"
                if not etype: continue
                timestamp = event.date.strftime(format_timestamp)
                if event.date <= last_timestamp: continue
                user = await self.bot.client.get_entity(PeerUser(event.user_id))
                msg = f"{timestamp} (UTC)\n{etype}\n{util.mention_user(user)} ({event.user_id})"
                await self.bot.client.send_message(self.logchannel, msg, schedule=timedelta(seconds=10))
            await asyncio.sleep(self.sleep)
