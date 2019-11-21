import os
import subprocess
import sys

import speedtest

from .. import command, module, util, listener


class SystemModule(module.Module):
    name = "System"

    async def on_load(self):
        self.restart_pending = False
        self.update_restart_pending = False

        self.db = self.bot.get_db("system")

    async def run_process(self, command, **kwargs):
        def _run_process():
            return subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, **kwargs
            )

        return await util.run_sync(_run_process)

    @command.desc("Run a snippet in a shell")
    @command.alias("sh")
    async def cmd_shell(self, msg, parsed_snip):
        if not parsed_snip:
            return "__Provide a snippet to run in shell.__"

        await msg.result("Running snippet...")
        before = util.time.usec()

        try:
            proc = await self.run_process(parsed_snip, shell=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "🕑 Snippet failed to finish within 2 minutes."

        after = util.time.usec()

        el_us = after - before
        el_str = f"\nTime: {util.time.format_duration_us(el_us)}"

        cmd_out = proc.stdout.strip()
        if not cmd_out:
            cmd_out = "(no output)"
        elif cmd_out[-1:] != "\n":
            cmd_out += "\n"

        err = f"⚠️ Return code: {proc.returncode}" if proc.returncode != 0 else ""

        return f"```{cmd_out}```{err}{el_str}"

    @command.desc("Get information about the host system")
    @command.alias("si")
    async def cmd_sysinfo(self, msg):
        await msg.result("Collecting system information...")

        try:
            proc = await self.run_process(["neofetch", "--stdout"], timeout=10)
        except subprocess.TimeoutExpired:
            return "🕑 `neofetch` failed to finish within 10 seconds."
        except FileNotFoundError:
            return "❌ The `neofetch` [program](https://github.com/dylanaraps/neofetch) must be installed on the host system."

        err = f"⚠️ Return code: {proc.returncode}" if proc.returncode != 0 else ""
        sysinfo = "\n".join(proc.stdout.strip().split("\n")[2:]) if proc.returncode == 0 else proc.stdout.strip()

        return f"```{sysinfo}```{err}"

    @command.desc("Test Internet speed")
    @command.alias("stest", "st")
    async def cmd_speedtest(self, msg):
        before = util.time.usec()

        st = await util.run_sync(speedtest.Speedtest)
        status = "Selecting server..."

        await msg.result(status)
        server = await util.run_sync(st.get_best_server)
        status += f" {server['sponsor']} ({server['name']})\n"
        status += "Ping: %.2f ms\n" % server["latency"]

        status += "Performing download test..."
        await msg.result(status)
        dl_bits = await util.run_sync(st.download)
        dl_mbit = dl_bits / 1000 / 1000
        status += " %.2f Mbps\n" % dl_mbit

        status += "Performing upload test..."
        await msg.result(status)
        ul_bits = await util.run_sync(st.upload)
        ul_mbit = ul_bits / 1000 / 1000
        status += " %.2f Mbps\n" % ul_mbit

        delta = util.time.usec() - before
        status += f"\nTime elapsed: {util.time.format_duration_us(delta)}"

        return status

    @command.desc("Restart the bot")
    @command.alias("re", "rst")
    async def cmd_restart(self, msg):
        await msg.result("Restarting bot...")

        # Save time and status message so we can update it after restarting
        await self.db.put("restart_status_chat_id", msg.chat_id)
        await self.db.put("restart_status_message_id", msg.id)
        await self.db.put("restart_time", util.time.usec())

        # Initiate the restart
        self.restart_pending = True
        self.log.info("Preparing to restart...")
        await self.bot.client.disconnect()

    async def on_start(self, time_us):
        # Update restart status message if applicable
        rs_time = await self.db.get("restart_time")
        if rs_time is not None:
            # Fetch status message info
            rs_chat_id = await self.db.get("restart_status_chat_id")
            rs_message_id = await self.db.get("restart_status_message_id")

            # Delete DB keys first in case message editing fails
            await self.db.delete("restart_time")
            await self.db.delete("restart_status_chat_id")
            await self.db.delete("restart_status_message_id")

            # Calculate and show duration
            duration = util.time.format_duration_us(util.time.usec() - rs_time)
            self.log.info(f"Bot restarted in {duration}")
            await self.bot.client.edit_message(rs_chat_id, rs_message_id, f"Bot restarted in {duration}.")

    async def on_stopped(self):
        # Restart the bot if applicable
        if self.restart_pending:
            self.log.info("Starting new bot instance...\n")
            os.execv(sys.argv[0], sys.argv)

    @command.desc("Update the bot from Git and restart")
    @command.alias("up", "upd")
    async def cmd_update(self, msg, remote_name):
        if not util.git.have_git:
            return "__The__ `git` __command is required for self-updating.__"

        if self.update_restart_pending:
            return await self.cmd_restart(msg)

        # Attempt to get the Git repo
        repo = await util.run_sync(lambda: util.git.get_repo())
        if not repo:
            return "__Unable to locate Git repository data.__"

        await msg.result("Pulling changes...")
        if remote_name:
            # Attempt to get reuqested remote
            try:
                remote = await util.run_sync(lambda: repo.remote(remote_name))
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
        self.log.info(f"Pulling from Git remote '{remote.name}'")
        await util.run_sync(remote.pull)

        # Don't restart yet if requirements were updated
        for change in old_commit.diff():
            if change.a_path == "requirements.txt":
                self.update_restart_pending = True
                return "Successfully pulled updates. Dependencies in `requirements.txt` were changed, so please update dependencies __before__ restarting the bot by re-running the `update` or `restart` command."

        # Restart after updating
        await self.cmd_restart(msg)
