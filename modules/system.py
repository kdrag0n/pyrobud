import subprocess
import command
import module
import util

class SystemModule(module.Module):
    name = 'System'

    async def run_process(self, command, **kwargs):
        def _run_process():
            return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)

        return await util.run_sync(_run_process)

    @command.desc('Run a snippet in a shell')
    @command.alias('sh')
    async def cmd_shell(self, msg, parsed_snip):
        if not parsed_snip:
            return '__Provide a snippet to run in shell.__'

        await msg.result('Running snippet...')
        before = util.time_us()
        try:
            proc = await self.run_process(parsed_snip, shell=True, timeout=120)
        except subprocess.TimeoutExpired:
            return '🕑 Snippet failed to finish within 2 minutes.'
        after = util.time_us()

        el_us = after - before
        el_str = f'\nTime: {util.format_duration_us(el_us)}'

        err = f'⚠️ Return code: {proc.returncode}' if proc.returncode != 0 else ''

        return f'```{proc.stdout.strip()}```{err}{el_str}'

    @command.desc('Get information about the host system')
    @command.alias('si')
    async def cmd_sysinfo(self, msg):
        await msg.result('Collecting system information...')

        try:
            proc = await self.run_process(['neofetch', '--stdout'], timeout=10)
        except subprocess.TimeoutExpired:
            return '🕑 `neofetch` failed to finish within 10 seconds.'

        err = f'⚠️ Return code: {proc.returncode}' if proc.returncode != 0 else ''
        sysinfo = '\n'.join(proc.stdout.strip().split('\n')[2:]) if proc.returncode == 0 else proc.stdout.strip()

        return f'```{sysinfo}```{err}'

    @command.desc('Test Internet speed')
    @command.alias('stest', 'st')
    async def cmd_speedtest(self, msg):
        await msg.result('Testing Internet speed; this may take a while...')

        before = util.time_us()
        try:
            proc = await self.run_process('speedtest', timeout=120)
        except subprocess.TimeoutExpired:
            return '🕑 `speedtest` failed to finish within 2 minutes.'
        after = util.time_us()

        el_us = after - before
        el_str = f'\nTime: {util.format_duration_us(el_us)}'

        err = f'⚠️ Return code: {proc.returncode}' if proc.returncode != 0 else ''

        out = proc.stdout.strip()
        if proc.returncode == 0:
            lines = out.split('\n')
            out = '\n'.join((lines[4], lines[6], lines[8])) # Server, down, up

        return f'```{out}```{err}{el_str}'
