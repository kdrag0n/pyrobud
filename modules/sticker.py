import subprocess
import tempfile
import command
import module
import time
import os
from PIL import Image

class StickerModule(module.Module):
    name = 'Sticker'

    def on_load(self):
        if 'stickers' not in self.bot.config:
            self.bot.config['stickers'] = {}
            print('Initialized saved sticker table in config')

        if 'user' not in self.bot.config:
            self.bot.config['user'] = {}
            print('Initialized user data table in config')

    def on_command(self, msg, cmd_info, args):
        self.bot.config['stats']['processed'] += 1

    @command.desc('Kang a sticker into configured/provided pack')
    def cmd_kang(self, msg, pack_name):
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to kang it.__'
        if 'sticker_pack' not in self.bot.config['user'] and not pack_name:
            return '__Specify a sticker pack name.__'
        if pack_name:
            self.bot.config['user']['sticker_pack'] = pack_name
            self.bot.save_config()
        else:
            pack_name = self.bot.config['user']['sticker_pack']

        self.bot.mresult(msg, 'Kanging...')

        st = msg.reply_to_message.sticker
        st_bot = 'Stickers'

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading sticker__'

            im = Image.open(path).convert('RGBA')
            im.save(f'{tmpdir}/sticker.png', 'png')

            self.bot.client.send_message(st_bot, '/addsticker')
            time.sleep(0.15)
            self.bot.client.send_message(st_bot, pack_name)
            time.sleep(0.15)
            self.bot.client.send_document(st_bot, f'{tmpdir}/sticker.png')
            time.sleep(0.25)

            if st.emoji:
                self.bot.client.send_message(st_bot, st.emoji)
            else:
                self.bot.client.send_message(st_bot, '❓')
            time.sleep(0.6)

            self.bot.client.send_message(st_bot, '/done')
            return f"[Kanged](https://t.me/addstickers/{pack_name})."

    @command.desc('Save a sticker with a name as reference')
    def cmd_save(self, msg, name):
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to save it.__'
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.bot.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        self.bot.config['stickers'][name] = msg.reply_to_message.sticker.file_id
        self.bot.save_config()

        return f'Sticker saved as `{name}`.'

    @command.desc('Save a sticker with a name to disk')
    def cmd_saved(self, msg, name):
        if not msg.reply_to_message or not msg.reply_to_message.sticker:
            return '__Reply to a sticker message to save it.__'
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.bot.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        path = self.bot.client.download_media(msg.reply_to_message, file_name=f'stickers/{name}01.webp')
        if not path:
            return '__Error downloading sticker__'

        self.bot.config['stickers'][name] = path
        self.bot.save_config()

        return f'Sticker saved to disk as `{name}`.'

    @command.desc('List saved stickers')
    def cmd_stickers(self, msg):
        if not self.bot.config['stickers']:
            return '__No stickers saved.__'

        out = 'Stickers saved:'

        for item in self.bot.config['stickers']:
            s_type = 'local' if self.bot.config['stickers'][item].endswith('.webp') else 'reference'
            out += f'\n    \u2022 **{item}** ({s_type})'

        return out

    @command.desc('List locally saved stickers')
    def cmd_stickersp(self, msg):
        if not self.bot.config['stickers']:
            return '__No stickers saved.__'

        out = 'Stickers saved:'

        for item in self.bot.config['stickers']:
            if self.bot.config['stickers'][item].endswith('.webp'):
                out += f'\n    \u2022 **{item}**'

        return out

    @command.desc('Delete a saved sticker')
    def cmd_sdel(self, msg, name):
        if not name: return '__Provide the name of a sticker to delete.__'

        s_type = 'local' if self.bot.config['stickers'][name].endswith('.webp') else 'reference'

        del self.bot.config['stickers'][name]
        self.bot.save_config()

        return f'{s_type.title()} sticker `{name}` deleted.'

    @command.desc('Get a sticker by name')
    def cmd_s(self, msg, name):
        if not name:
            self.bot.mresult(msg, '__Provide the name of a sticker.__')
            return
        if name not in self.bot.config['stickers']:
            self.bot.mresult(msg, '__That sticker doesn\'t exist.__')
            return

        chat_id = msg.chat.id
        reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None
        self.bot.mresult(msg, 'Uploading sticker...')
        self.bot.client.send_sticker(chat_id, self.bot.config['stickers'][name], reply_to_message_id=reply_id)
        self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Get a sticker by name and send it as a photo')
    def cmd_sp(self, msg, name):
        if not name:
            self.bot.mresult(msg, '__Provide the name of a sticker.__')
            return
        if name not in self.bot.config['stickers']:
            self.bot.mresult(msg, '__That sticker doesn\'t exist.__')
            return

        if not self.bot.config['stickers'][name].endswith('.webp'):
            self.bot.mresult(msg, '__That sticker can not be sent as a photo.__')
            return

        chat_id = msg.chat.id
        reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None

        path = self.bot.config['stickers'][name]
        if not os.path.isfile(path + '.png'):
            im = Image.open(path).convert('RGBA')
            im.save(path + '.png', 'png')

        self.bot.mresult(msg, 'Uploading sticker...')
        self.bot.client.send_photo(chat_id, path + '.png', reply_to_message_id=reply_id)
        self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Sticker an image')
    def cmd_sticker(self, msg, pack):
        if not msg.reply_to_message or (not msg.reply_to_message.photo and not msg.reply_to_message.document):
            self.bot.mresult(msg, '__Reply to a message with an image to sticker it.__')
            return
        if not pack:
            self.bot.mresult(msg, '__Provide the name of the pack to add the sticker to.__')
            return

        ps = pack.split()
        emoji = ps[1] if len(ps) > 1 else '❓'

        self.bot.mresult(msg, 'Stickering...')

        st_bot = 'Stickers'

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading image__'

            im = Image.open(path).convert('RGBA')

            sz = im.size
            target = 512
            if sz[0] > sz[1]:
                w_ratio = target / float(sz[0])
                h_size = int(float(sz[1]) * float(w_ratio))
                im = im.resize((target, h_size), Image.LANCZOS)
            else:
                h_ratio = target / float(sz[1])
                w_size = int(float(sz[0]) * float(h_ratio))
                im = im.resize((w_size, target), Image.LANCZOS)

            im.save(f'{tmpdir}/sticker.png', 'png')

            self.bot.client.send_message(st_bot, '/addsticker')
            time.sleep(0.15)
            self.bot.client.send_message(st_bot, ps[0])
            time.sleep(0.15)
            self.bot.client.send_document(st_bot, f'{tmpdir}/sticker.png')
            time.sleep(0.15)

            self.bot.client.send_message(st_bot, emoji)
            time.sleep(0.6)

            self.bot.client.send_message(st_bot, '/done')
            self.bot.mresult(msg, f'[Stickered](https://t.me/addstickers/{ps[0]}). Preview:')

            im.save(f'{tmpdir}/sticker.webp', 'webp')
            self.bot.client.send_sticker(msg.chat.id, f'{tmpdir}/sticker.webp')

    @command.desc('Sticker an image and save it to disk')
    def cmd_qstick(self, msg, name):
        if not msg.reply_to_message or (not msg.reply_to_message.photo and not msg.reply_to_message.document):
            self.bot.mresult(msg, '__Reply to a message with an image to sticker it.__')
            return
        if not name:
            return '__Provide a name to save the sticker as.__'
        if name in self.bot.config['stickers']:
            return '__There\'s already a sticker with that name.__'

        self.bot.mresult(msg, 'Stickering...')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading image__'

            im = Image.open(path).convert('RGBA')

            sz = im.size
            target = 512
            if sz[0] > sz[1]:
                w_ratio = target / float(sz[0])
                h_size = int(float(sz[1]) * float(w_ratio))
                im = im.resize((target, h_size), Image.LANCZOS)
            else:
                h_ratio = target / float(sz[1])
                w_size = int(float(sz[0]) * float(h_ratio))
                im = im.resize((w_size, target), Image.LANCZOS)

            im.save(f'stickers/{name}01.webp', 'webp')

            self.bot.config['stickers'][name] = f'stickers/{name}01.webp'
            self.bot.save_config()

            return f'Sticker saved to disk as `{name}`.'

    @command.desc('Glitch an image')
    def cmd_glitch(self, msg, boffset_str):
        if not msg.reply_to_message or (not msg.reply_to_message.photo and not msg.reply_to_message.document):
            self.bot.mresult(msg, '__Reply to a message with an image to glitch it.__')
            return

        boffset = 8
        if boffset_str:
            try:
                boffset = int(boffset_str)
            except ValueError:
                return '__Invalid distorted block offset strength.__'

        self.bot.mresult(msg, 'Glitching...')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading sticker image__'

            im = Image.open(path).convert('RGBA')
            im.save(path + '.png', 'png')

            subprocess.run(['corrupter', '-boffset', str(boffset), path + '.png', path + '_glitch.png'])

            chat_id = msg.chat.id
            reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None
            self.bot.mresult(msg, 'Uploading glitched image...')
            self.bot.client.send_photo(chat_id, path + '_glitch.png', reply_to_message_id=reply_id)
            self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)
