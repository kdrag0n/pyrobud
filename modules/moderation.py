import command
import module
import util
import time

class ModerationModule(module.Module):
    name = 'Moderation'

    def on_load(self):
        if 'antibot' not in self.bot.config:
            self.bot.config['antibot'] = {
                'threshold_time': 5,
                'group_ids': []
            }
        else:
            if 'threshold_time' not in self.bot.config['antibot']:
                self.bot.config['antibot']['threshold_time'] = 5
            if 'group_ids' not in self.bot.config['antibot']:
                self.bot.config['antibot']['group_ids'] = []

    def contains_link(self, text):
        if not text:
            return False

        return 'https://' in text or 'http://' in text or 't.me/' in text

    def is_suspicious(self, msg):
        return msg.forward_from or msg.forward_from_name or msg.forward_from_chat or msg.forward_from_message_id or self.contains_link(msg.text)

    def on_message(self, msg):
        if msg.chat and msg.chat.type == "supergroup" and msg.chat.id in self.bot.config['antibot']['group_ids'] and msg.from_user and msg.from_user.id != self.bot.uid and msg.date and self.is_suspicious(msg):
            member = self.bot.client.get_chat_member(msg.chat.id, msg.from_user.id)
            if not member.date:
                return
            
            delta = msg.date - member.date
            if delta <= self.bot.config['antibot']['threshold_time']:
                # This is probably a spambot, ban the user
                self.bot.client.send_message(msg.chat.id, f'/ban Auto-detected spambot - user ID: `{msg.from_user.id}``', reply_to_message_id=msg.message_id)
                time.sleep(1)
                self.bot.client.delete_messages(msg.chat.id, msg.message_id, revoke=True)

    @command.desc('Toggle the antibot auto-moderation feature in this group')
    def cmd_antibot(self, msg):
        if not msg.chat or msg.chat.type != "supergroup":
            return "__This chat isn't eligible for antibot.__"

        state = msg.chat.id in self.bot.config['antibot']['group_ids']
        state = not state

        if state:
            self.bot.config['antibot']['group_ids'].append(msg.chat.id)
        else:
            self.bot.config['antibot']['group_ids'].remove(msg.chat.id)
        self.bot.save_config()

        status = 'enabled' if state else 'disabled'
        return f'Antibot is now **{status}** in this group.'
