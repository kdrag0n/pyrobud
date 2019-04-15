import subprocess
import command
import module
import util

class SystemModule(module.Module):
    name = 'System'

    @command.desc('Run a snippet in a shell')
    def cmd_shell(self, msg, snip):
        if not snip:
            return '__Provide a snippet to run in shell.__'
        snip = util.filter_input_block(snip)

        before = util.time_us()
        try:
            proc = subprocess.run(snip, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, text=True)
        except subprocess.TimeoutExpired:
            return '🕑 Snippet took longer than 2 minutes to run.'
        after = util.time_us()

        el_us = after - before
        el_str = f'\nTime: {util.format_duration_us(el_us)}'

        err = f'⚠️ Return code: {proc.returncode}' if proc.returncode != 0 else ''

        return f'```{proc.stdout.strip()}```{err}{el_str}'

    @command.desc('Get information about the host system')
    def cmd_sysinfo(self, msg, snip):
        try:
            proc = subprocess.run(['neofetch', '--stdout'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10, text=True)
        except subprocess.TimeoutExpired:
            return '🕑 `neofetch` took longer than 10 seconds to run.'
        err = f'⚠️ Return code: {proc.returncode}' if proc.returncode != 0 else ''

        return f'```{proc.stdout.strip()}```{err}'
