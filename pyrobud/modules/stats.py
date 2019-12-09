from .. import command, module, util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24


class StatsModule(module.Module):
    name = "Stats"

    async def on_load(self):
        self.db = self.bot.get_db("stats")

        # Log migration message if applicable
        if await self.db.has("stop_time_usec") or await self.db.has("uptime"):
            self.log.info("Migrating stats timekeeping format")

        # Perform last stop_time_usec increment to prepare for migration
        last_time = await self.db.get("stop_time_usec")
        if last_time is not None:
            await self.db.inc("uptime", util.time.usec() - last_time)
            await self.db.delete("stop_time_usec")

        # Migrate old stop_time_usec + uptime timekeeping format to new start_time_usec
        uptime = await self.db.get("uptime")
        if uptime is not None:
            await self.db.put("start_time_usec", util.time.usec() - uptime)
            await self.db.delete("uptime")

    async def on_start(self, time_us):
        # Initialize start_time_usec for new instances
        if not await self.db.has("start_time_usec"):
            await self.db.put("start_time_usec", util.time.usec())

    async def on_message(self, msg):
        stat = "sent" if msg.out else "received"
        await self.bot.dispatch_event("stat_event", stat)

        if msg.sticker:
            sticker_stat = stat + "_stickers"
            await self.bot.dispatch_event("stat_event", sticker_stat)

    async def on_message_edit(self, msg):
        stat = "sent" if msg.out else "received"
        await self.bot.dispatch_event("stat_event", stat + "_edits")

    async def on_command(self, msg, cmd_info, args):
        await self.bot.dispatch_event("stat_event", "processed")

    async def on_stat_event(self, key):
        await self.db.inc(key)

    def calc_pct(self, num1, num2):
        if not num2:
            return "0"

        return "{:.1f}".format((num1 / num2) * 100).rstrip("0").rstrip(".")

    def calc_ph(self, stat, uptime):
        up_hr = max(1, uptime) / USEC_PER_HOUR
        return "{:.1f}".format(stat / up_hr).rstrip("0").rstrip(".")

    def calc_pd(self, stat, uptime):
        up_day = max(1, uptime) / USEC_PER_DAY
        return "{:.1f}".format(stat / up_day).rstrip("0").rstrip(".")

    @command.desc("Show chat stats (pass `reset` to reset stats)")
    @command.usage('["reset" to reset stats?]', optional=True)
    @command.alias("stat")
    async def cmd_stats(self, ctx: command.Context):
        if ctx.input == "reset":
            await self.db.clear()
            await self.on_load()
            await self.on_start(util.time.usec())
            return "__All stats have been reset.__"

        start_time = await self.db.get("start_time_usec")
        uptime = util.time.usec() - start_time

        sent = await self.db.get("sent", 0)
        sent_stickers = await self.db.get("sent_stickers", 0)
        sent_edits = await self.db.get("sent_edits", 0)
        recv = await self.db.get("received", 0)
        recv_stickers = await self.db.get("received_stickers", 0)
        recv_edits = await self.db.get("received_edits", 0)
        processed = await self.db.get("processed", 0)
        replaced = await self.db.get("replaced", 0)
        ab_kicked = await self.db.get("spambots_banned", 0)
        stickers = await self.db.get("stickers_created", 0)

        return f"""**Stats since last reset**:
    • **Total time elapsed**: {util.time.format_duration_us(uptime)}
    • **Messages received**: {recv} ({self.calc_ph(recv, uptime)}/h) • {self.calc_pct(recv_stickers, recv)}% are stickers • {self.calc_pct(recv_edits, recv)}% were edited
    • **Messages sent**: {sent} ({self.calc_ph(sent, uptime)}/h) • {self.calc_pct(sent_stickers, sent)}% are stickers • {self.calc_pct(sent_edits, sent)}% were edited
    • **Total messages sent**: {self.calc_pct(sent, sent + recv)}% of all accounted messages
    • **Commands processed**: {processed} ({self.calc_ph(processed, uptime)}/h) • {self.calc_pct(processed, sent)}% of sent messages
    • **Snippets replaced**: {replaced} ({self.calc_ph(replaced, uptime)}/h) • {self.calc_pct(replaced, sent)}% of sent messages
    • **Spambots kicked**: {ab_kicked} ({self.calc_pd(ab_kicked, uptime)}/day)
    • **Stickers created**: {stickers} ({self.calc_pd(stickers, uptime)}/day)"""
