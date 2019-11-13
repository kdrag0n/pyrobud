import module, asyncio, time
from datetime import datetime, timedelta

class DynamicPosts(module.Module):
    name = "Dynamic Posts"
    sleep = timedelta(minutes=15).total_seconds()
    enabled = True

    posts = {
        19: "Timezone: `{timezone}`\nLocal time: `{time}`",
        20: "{botinfo}",
        21: "{sysinfo}",
        22: "{stats}"
    }
    channel = -1001441900591
    async def on_ready(self):
        self.bot.loop.create_task(self.updatePosts())

    async def updatePosts(self):
        while self.enabled:
            await asyncio.sleep(self.sleep)
            for msgid, text in self.posts.items():
                try:
                    await self.bot.client.edit_message(self.channel, msgid, text.format(
                        timezone=time.strftime('%Z%z'),
                        time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        botinfo=await self.bot.modules["Debug"].cmd_botinfo(None, False),
                        sysinfo=await self.bot.modules["System"].cmd_sysinfo(None),
                        stats=await self.bot.modules["Stats"].cmd_stats(None, None)
                     ))
                    await asyncio.sleep(5)
                except: print("error while processing msg #", msgid)


    async def cmd_dynamicposts(self, msg):
        self.enabled = not self.enabled
        return ("Enabled" if self.enabled else "Disabled") + " Dynamic Posts"
