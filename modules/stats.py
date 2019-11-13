import command
import module
import util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24


class StatsModule(module.Module):
    name = "Stats"

    async def on_load(self):
        # Populate config if necessary
        if "stats" not in self.bot.config:
            self.bot.config["stats"] = {}

        keys = [
            "sent",
            "received",
            "processed",
            "replaced",
            "sent_edits",
            "received_edits",
            "sent_stickers",
            "received_stickers",
            "uptime",
            "spambots_banned",
            "stickers_created",
        ]

        for k in keys:
            if k not in self.bot.config["stats"]:
                self.bot.config["stats"][k] = 0

    async def on_start(self, time_us):
        if "stop_time_usec" in self.bot.config["stats"]:
            self.last_time = self.bot.config["stats"]["stop_time_usec"]
            del self.bot.config["stats"]["stop_time_usec"]
        else:
            self.last_time = time_us

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
        self.bot.config["stats"][key] += 1
        self.update_uptime()

    def update_uptime(self):
        now = util.time_us()
        delta_us = now - self.last_time
        self.bot.config["stats"]["uptime"] += delta_us
        self.last_time = now

    async def on_stop(self):
        self.update_uptime()
        self.bot.config["stats"]["stop_time_usec"] = self.last_time

    def calc_pct(self, num1: int, num2: int) -> str:
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
    @command.alias("stat")
    async def cmd_stats(self, msg, args):
        if args == "reset":
            self.bot.config["stats"] = {}
            await self.on_load()
            await self.on_start(util.time_us())
            return "__All stats have been reset.__"

        self.update_uptime()
        await self.bot.save_config()

        st = self.bot.config["stats"]
        uptime = st["uptime"]
        sent = st["sent"]
        sent_stickers = st["sent_stickers"]
        sent_edits = st["sent_edits"]
        recv = st["received"]
        recv_stickers = st["received_stickers"]
        recv_edits = st["received_edits"]
        processed = st["processed"]
        replaced = st["replaced"]
        banned = st["spambots_banned"]
        stickers = st["stickers_created"]

        return f"""**Stats since last reset**:
    • **Total time elapsed**: {util.format_duration_us(uptime)}
    • **Messages received**: {recv} ({self.calc_ph(recv, uptime)}/h) • {self.calc_pct(recv_stickers, recv)}% are stickers • {self.calc_pct(recv_edits, recv)}% were edited
    • **Messages sent**: {sent} ({self.calc_ph(sent, uptime)}/h) • {self.calc_pct(sent_stickers, sent)}% are stickers • {self.calc_pct(sent_edits, sent)}% were edited
    • **Total messages sent**: {self.calc_pct(sent, sent + recv)}% of all accounted messages
    • **Commands processed**: {processed} ({self.calc_ph(processed, uptime)}/h) • {self.calc_pct(processed, sent)}% of sent messages
    • **Snippets replaced**: {replaced} ({self.calc_ph(replaced, uptime)}/h) • {self.calc_pct(replaced, sent)}% of sent messages
    • **Spambots banned**: {banned} ({self.calc_pd(banned, uptime)}/day)
    • **Stickers created**: {stickers} ({self.calc_pd(stickers, uptime)}/day)"""
