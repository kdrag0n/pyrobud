import requests
import tempfile
import command
import module
import os

class UploadModule(module.Module):
    name = 'Upload'

    @command.desc('Paste message text to Hastebin')
    @command.alias('hs')
    def cmd_haste(self, msg, text):
        orig = msg.reply_to_message
        if orig is None:
            if text:
                txt = text
            else:
                return '__Reply to a message or provide text in command.__'
        else:
            txt = orig.text
            if not txt:
                if orig.document:
                    def prog_func(cl, current, total):
                        self.bot.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

                    with tempfile.TemporaryDirectory() as tmpdir:
                        path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
                        if not path:
                            return '__Error downloading file__'

                        with open(path, 'rb') as f:
                            txt = f.read().decode('utf-8')
                else:
                    return '__Reply to a message with text or a text file, or provide text in command.__'

        self.bot.mresult(msg, 'Uploading text to [Hastebin](https://hastebin.com/)...')
        resp = requests.post('https://hastebin.com/documents', data=txt).json()
        return f'https://hastebin.com/{resp["key"]}'

    @command.desc('Paste message text to Dogbin')
    def cmd_dog(self, msg, text):
        orig = msg.reply_to_message
        if orig is None:
            if text:
                txt = text
            else:
                return '__Reply to a message or provide text in command.__'
        else:
            txt = orig.text
            if not txt:
                if orig.document:
                    def prog_func(cl, current, total):
                        self.bot.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

                    with tempfile.TemporaryDirectory() as tmpdir:
                        path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
                        if not path:
                            return '__Error downloading file__'

                        with open(path, 'rb') as f:
                            txt = f.read().decode('utf-8')
                else:
                    return '__Reply to a message with text or a text file, or provide text in command.__'

        self.bot.mresult(msg, 'Uploading text to [Dogbin](https://del.dog/)...')
        resp = requests.post('https://del.dog/documents', data=txt).json()
        return f'https://del.dog/{resp["key"]}'

    @command.desc('Upload replied-to file to file.io')
    def cmd_fileio(self, msg, expires):
        if msg.reply_to_message is None:
            return '__Reply to a message with the file to upload.__'

        if expires == 'help':
            return '__Expiry format: 1y/12m/52w/365d__'
        elif expires:
            if expires[-1] not in ['y', 'm', 'w', 'd']:
                return '__Unknown unit. Expiry format: 1y/12m/52w/365d__'
            else:
                try:
                    int(expires[:-1])
                except ValueError:
                    return '__Invalid number. Expiry format: 1y/12m/52w/365d__'
        else:
            expires = '2d'

        def prog_func(cl, current, total):
            self.bot.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
            if not path:
                return '__Error downloading file__'

            self.bot.mresult(msg, 'Uploading file to [file.io](https://file.io/)...')
            with open(path, 'rb') as f:
                resp = requests.post(f'https://file.io/?expires={expires}', files={'file': f}).json()

            if not resp['success']:
                return '__Error uploading file__'

            return resp['link']

    @command.desc('Upload replied-to file to transfer.sh')
    def cmd_transfer(self, msg):
        if msg.reply_to_message is None:
            return '__Reply to a message with the file to upload.__'

        def prog_func(cl, current, total):
            self.bot.mresult(msg, f'Downloading...\nProgress: `{float(current) / 1000.0}/{float(total) / 1000.0}` KB')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/', progress=prog_func, progress_args=())
            if not path:
                return '__Error downloading file__'

            self.bot.mresult(msg, 'Uploading file to [transfer.sh](https://transfer.sh/)...')
            with open(path, 'rb') as f:
                resp = requests.put(f'https://transfer.sh/{os.path.basename(path)}', data=f)

            if not resp.ok:
                return '__Error uploading file__'

            return resp.text
