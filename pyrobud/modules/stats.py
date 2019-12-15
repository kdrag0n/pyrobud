from typing import ClassVar, Optional

import telethon as tg

from .. import command, module, util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24


def calc_pct(num1: int, num2: int) -> str:
    if not num2:
        return "0"

    return "{:.1f}".format((num1 / num2) * 100).rstrip("0").rstrip(".")


def calc_ph(stat: int, uptime: int) -> str:
    up_hr = max(1, uptime) / USEC_PER_HOUR
    return "{:.1f}".format(stat / up_hr).rstrip("0").rstrip(".")


def calc_pd(stat: int, uptime: int) -> str:
    up_day = max(1, uptime) / USEC_PER_DAY
    return "{:.1f}".format(stat / up_day).rstrip("0").rstrip(".")


class StatsModule(module.Module):
    name: ClassVar[str] = "Stats"
    db: util.db.AsyncDB

    async def on_load(self) -> None:
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

    async def on_start(self, time_us: int) -> None:
        # Initialize start_time_usec for new instances
        if not await self.db.has("start_time_usec"):
            await self.db.put("start_time_usec", time_us)

    async def on_message(self, msg: tg.events.NewMessage.Event) -> None:
        stat = "sent" if msg.out else "received"
        await self.bot.dispatch_event("stat_event", stat)

        if msg.sticker:
            sticker_stat = stat + "_stickers"
            await self.bot.dispatch_event("stat_event", sticker_stat)

    async def on_message_edit(self, msg: tg.events.MessageEdited.Event) -> None:
        stat = "sent" if msg.out else "received"
        await self.bot.dispatch_event("stat_event", stat + "_edits")

    async def on_command(self, cmd: command.Command, msg: tg.events.MessageEdited.Event) -> None:
        await self.bot.dispatch_event("stat_event", "processed")

    async def on_stat_event(self, key: str) -> None:
        await self.db.inc(key)

    @command.desc("Show chat stats (pass `reset` to reset stats)")
    @command.usage('["reset" to reset stats?]', optional=True)
    @command.alias("stat")
    async def cmd_stats(self, ctx: command.Context) -> str:
        if ctx.input == "reset":
            await self.db.clear()
            await self.on_load()
            await self.on_start(util.time.usec())
            return "__All stats have been reset.__"

        start_time: Optional[int] = await self.db.get("start_time_usec")
        if start_time is None:
            start_time = util.time.usec()
            await self.db.put("start_time_usec", start_time)
        uptime = util.time.usec() - start_time

        sent: int = await self.db.get("sent", 0)
        sent_stickers: int = await self.db.get("sent_stickers", 0)
        sent_edits: int = await self.db.get("sent_edits", 0)
        recv: int = await self.db.get("received", 0)
        recv_stickers: int = await self.db.get("received_stickers", 0)
        recv_edits: int = await self.db.get("received_edits", 0)
        processed: int = await self.db.get("processed", 0)
        replaced: int = await self.db.get("replaced", 0)
        ab_kicked: int = await self.db.get("spambots_banned", 0)
        stickers: int = await self.db.get("stickers_created", 0)

        return f"""**Stats since last reset**:
    • **Total time elapsed**: {util.time.format_duration_us(uptime)}
    • **Messages received**: {recv} ({calc_ph(recv, uptime)}/h) • {calc_pct(recv_stickers, recv)}% are stickers • {calc_pct(recv_edits, recv)}% were edited
    • **Messages sent**: {sent} ({calc_ph(sent, uptime)}/h) • {calc_pct(sent_stickers, sent)}% are stickers • {calc_pct(sent_edits, sent)}% were edited
    • **Total messages sent**: {calc_pct(sent, sent + recv)}% of all accounted messages
    • **Commands processed**: {processed} ({calc_ph(processed, uptime)}/h) • {calc_pct(processed, sent)}% of sent messages
    • **Snippets replaced**: {replaced} ({calc_ph(replaced, uptime)}/h) • {calc_pct(replaced, sent)}% of sent messages
    • **Spambots kicked**: {ab_kicked} ({calc_pd(ab_kicked, uptime)}/day)
    • **Stickers created**: {stickers} ({calc_pd(stickers, uptime)}/day)"""
