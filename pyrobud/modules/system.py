import asyncio
import os
import sys
from pathlib import Path
from typing import ClassVar, Optional

import speedtest

from .. import command, module, util


class SystemModule(module.Module):
    name: ClassVar[str] = "System"
    restart_pending: bool
    db: util.db.AsyncDB

    async def on_load(self):
        self.restart_pending = False

        self.db = self.bot.get_db("system")

    @command.desc("Run a snippet in a shell")
    @command.usage("[shell snippet]")
    @command.alias("sh")
    async def cmd_shell(self, ctx: command.Context) -> str:
        snip = ctx.input

        await ctx.respond("Running snippet...")
        before = util.time.usec()

        try:
            stdout, _, ret = await util.system.run_command_shell(snip, timeout=120)
        except asyncio.TimeoutError:
            return "🕑 Snippet failed to finish within 2 minutes."

        after = util.time.usec()

        el_us = after - before
        el_str = f"\nTime: {util.time.format_duration_us(el_us)}"

        cmd_out = stdout.decode().strip()
        if not cmd_out:
            cmd_out = "(no output)"
        elif cmd_out[-1:] != "\n":
            cmd_out += "\n"

        err = f"⚠️ Return code: {ret}" if ret != 0 else ""
        return f"```{cmd_out}```{err}{el_str}"

    @command.desc("Get information about the host system")
    @command.alias("si")
    async def cmd_sysinfo(self, ctx: command.Context) -> str:
        await ctx.respond("Collecting system information...")

        try:
            stdout, _, ret = await util.system.run_command(
                "neofetch", "--stdout", timeout=10
            )
        except asyncio.TimeoutError:
            return "🕑 `neofetch` failed to finish within 10 seconds."
        except FileNotFoundError:
            return "❌ [neofetch](https://github.com/dylanaraps/neofetch) must be installed on the host system."

        err = f"⚠️ Return code: {ret}" if ret != 0 else ""
        sysinfo = (
            "\n".join(stdout.decode().strip().split("\n")[2:])
            if ret == 0
            else stdout.strip()
        )

        return f"```{sysinfo}```{err}"

    @command.desc("Test Internet speed")
    @command.alias("stest", "st")
    async def cmd_speedtest(self, ctx: command.Context) -> str:
        before = util.time.usec()

        st = await util.run_sync(speedtest.Speedtest)
        status = "Selecting server..."

        await ctx.respond(status)
        server = await util.run_sync(st.get_best_server)
        status += f" {server['sponsor']} ({server['name']})\n"
        status += f"Ping: {server['latency']:.2f} ms\n"

        status += "Performing download test..."
        await ctx.respond(status)
        dl_bits = await util.run_sync(st.download)
        dl_mbit = dl_bits / 1000 / 1000
        status += f" {dl_mbit:.2f} Mbps\n"

        status += "Performing upload test..."
        await ctx.respond(status)
        ul_bits = await util.run_sync(st.upload)
        ul_mbit = ul_bits / 1000 / 1000
        status += f" {ul_mbit:.2f} Mbps\n"

        delta = util.time.usec() - before
        status += f"\nTime elapsed: {util.time.format_duration_us(delta)}"

        return status

    @command.desc("Stop this bot")
    async def cmd_stop(self, ctx: command.Context) -> None:
        await ctx.respond("Stopping bot...")
        await self.bot.client.disconnect()

    @command.desc("Restart this bot")
    @command.alias("re", "rst")
    async def cmd_restart(self, ctx: command.Context, *, reason="manual") -> None:
        resp_msg = await ctx.respond("Restarting bot...")

        # Save time and status message so we can update it after restarting
        await self.db.put("restart_status_chat_id", resp_msg.chat_id)
        await self.db.put("restart_status_message_id", resp_msg.id)
        await self.db.put("restart_time", util.time.usec())
        await self.db.put("restart_reason", reason)

        # Initiate the restart
        self.restart_pending = True
        self.log.info("Preparing to restart...")
        await self.bot.client.disconnect()

    async def on_start(self, time_us: int) -> None:
        # Update restart status message if applicable
        rs_time: Optional[int] = await self.db.get("restart_time")
        if rs_time is not None:
            # Fetch status message info
            rs_chat_id: Optional[int] = await self.db.get("restart_status_chat_id")
            rs_message_id: Optional[int] = await self.db.get(
                "restart_status_message_id"
            )
            rs_reason: Optional[str] = await self.db.get("restart_reason")

            # Delete DB keys first in case message editing fails
            await self.db.delete("restart_time")
            await self.db.delete("restart_status_chat_id")
            await self.db.delete("restart_status_message_id")
            await self.db.delete("restart_reason")

            # Bail out if we're missing necessary values
            if rs_chat_id is None or rs_message_id is None:
                return

            # Show message
            updated = "updated and " if rs_reason == "update" else ""
            duration = util.time.format_duration_us(util.time.usec() - rs_time)
            self.log.info(f"Bot {updated}restarted in {duration}")
            status_msg = await self.bot.client.get_messages(
                rs_chat_id, ids=rs_message_id
            )
            await self.bot.respond(status_msg, f"Bot {updated}restarted in {duration}.")

    async def on_stopped(self) -> None:
        # Restart the bot if applicable
        if self.restart_pending:
            self.log.info("Starting new bot instance...\n")
            # This is safe because original arguments are reused. skipcq: BAN-B606
            os.execv(sys.executable, (sys.executable, *sys.argv))

    @command.desc("Update this bot from Git and restart")
    @command.usage("[remote name?]", optional=True)
    @command.alias("up", "upd")
    async def cmd_update(self, ctx: command.Context) -> Optional[str]:
        remote_name = ctx.input

        if not util.git.have_git:
            return "__The__ `git` __command is required for self-updating.__"

        # Attempt to get the Git repo
        repo = await util.run_sync(util.git.get_repo)
        if not repo:
            return "__Unable to locate Git repository data.__"

        if remote_name:
            # Attempt to get requested remote
            try:
                remote = await util.run_sync(repo.remote, remote_name)
            except ValueError:
                return f"__Remote__ `{remote_name}` __not found.__"
        else:
            # Get current branch's tracking remote
            remote = await util.run_sync(util.git.get_current_remote)
            if remote is None:
                return f"__Current branch__ `{repo.active_branch.name}` __is not tracking a remote.__"

        # Save old commit for diffing
        old_commit = await util.run_sync(repo.commit)

        # Pull from remote
        await ctx.respond(f"Pulling changes from `{remote}`...")
        await util.run_sync(remote.pull)

        # Return early if no changes were pulled
        diff = old_commit.diff()
        if not diff:
            return "No updates found."

        # Check for dependency changes
        if any(change.a_path == "poetry.lock" for change in diff):
            # Update dependencies automatically if running in venv
            prefix = util.system.get_venv_path()
            if prefix:
                pip = str(Path(prefix) / "bin" / "pip")

                await ctx.respond("Updating dependencies...")
                stdout, _, ret = await util.system.run_command(
                    pip, "install", repo.working_tree_dir
                )
                if ret != 0:
                    return f"""⚠️ Error updating dependencies:

```{stdout.decode()}```

Fix the issue manually and then restart the bot."""
            else:
                return f"""Successfully pulled updates.

**Update dependencies manually** to avoid errors, then restart the bot for the update to take effect.

Dependency updates are automatic if you're running the bot in a virtualenv."""

        # Restart after updating
        await self.cmd_restart(ctx, reason="update")
        return None
