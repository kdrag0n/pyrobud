import subprocess
import tempfile
import command
import module
import time
import os
from PIL import Image

class LengthMismatchError(Exception):
    pass

class StickerModule(module.Module):
    name = 'Sticker'

    def on_load(self):
        if 'stickers' not in self.bot.config:
            self.bot.config['stickers'] = {}
            print('Initialized saved sticker table in config')

        if 'user' not in self.bot.config:
            self.bot.config['user'] = {}
            print('Initialized user data table in config')

    def add_sticker(self, png_path, pack_name, emoji, jpg_path=None):
        if not emoji:
            emoji = '❓'

        st_bot = 'Stickers'

        self.bot.client.send_message(st_bot, '/addsticker')
        time.sleep(0.15)
        self.bot.client.send_message(st_bot, pack_name)
        time.sleep(0.15)
        self.bot.client.send_document(st_bot, png_path)
        time.sleep(0.25)
        self.bot.client.send_message(st_bot, emoji)
        time.sleep(0.6)

        self.bot.client.send_message(st_bot, '/done')
        return f'https://t.me/addstickers/{pack_name}'

    def img_to_png(self, src, dest):
        im = Image.open(src).convert('RGBA')
        im.save(dest, 'png')

    def img_to_sticker(self, src, dests, formats):
        if not dests or not formats:
            return
        if len(dests) != len(formats):
            raise LengthMismatchError(f'Length mismatch: {len(dests)} destination paths and {len(formats)} formats given')

        im = Image.open(src).convert('RGBA')

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

        for i, dest in enumerate(dests):
            im.save(dest, formats[i])

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

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.bot.client.download_media(msg.reply_to_message, file_name=tmpdir + '/')
            if not path:
                return '__Error downloading sticker__'

            new_path = f'{tmpdir}/sticker.png'
            self.img_to_png(path, new_path)

            link = self.add_sticker(new_path, pack_name, st.emoji)
            self.log_stat('stickers_created')

            return f"[Kanged]({link})."

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
        png_path = path + '.png'
        if not os.path.isfile(png_path):
            self.img_to_png(path, png_path)

        self.bot.mresult(msg, 'Uploading sticker...')
        self.bot.client.send_photo(chat_id, png_path, reply_to_message_id=reply_id)
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

            new_path = f'{tmpdir}/sticker.png'
            webp_path = f'{tmpdir}/sticker.webp'
            self.img_to_sticker(path, [new_path, webp_path], ['png', 'webp'])

            link = self.add_sticker(new_path, ps[0], emoji)
            self.log_stat('stickers_created')
            self.bot.mresult(msg, f'[Stickered]({link}). Preview:')

            # Send a preview
            self.bot.client.send_sticker(msg.chat.id, webp_path)

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

            new_path = f'stickers/{name}01.webp'
            self.img_to_sticker(path, [new_path], ['webp'])

            self.bot.config['stickers'][name] = new_path
            self.bot.save_config()

            self.log_stat('stickers_created')
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

            png_path = path + '.png'
            self.img_to_png(path, png_path)

            subprocess.run(['corrupter', '-boffset', str(boffset), png_path, path + '_glitch.png'])

            chat_id = msg.chat.id
            reply_id = msg.reply_to_message.message_id if msg.reply_to_message else None
            self.bot.mresult(msg, 'Uploading glitched image...')
            self.bot.client.send_photo(chat_id, path + '_glitch.png', reply_to_message_id=reply_id)
            self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)
