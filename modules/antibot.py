import command
import module
import util
import time

class AntibotModule(module.Module):
    name = 'Antibot'

    suspicious_keywords = [
        'investment',
        'profit',
        'binance',
        'binanse',
        'bitcoin',
        'testnet'
    ]

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

    def msg_has_suspicious_entity(self, msg):
        if not msg.entities:
            return False

        for entity in msg.entities:
            if entity.type == 'url' or entity.type == 'text_link':
                return True
            if entity.type == 'email':
                return True
            if entity.type == 'phone_number':
                return True

        return False

    def msg_is_forwarded(self, msg):
        return msg.forward_from or msg.forward_from_name or msg.forward_from_chat or msg.forward_from_message_id

    def msg_has_suspicious_keyword(self, msg):
        if not msg.text:
            return False

        l_text = msg.text.lower()
        for kw in self.__class__.suspicious_keywords:
            if kw in l_text:
                return True

        return False

    def msg_content_suspicious(self, msg):
        return self.msg_is_forwarded(msg) or self.msg_has_suspicious_entity(msg) or self.msg_has_suspicious_keyword(msg)

    def msg_is_suspicious(self, msg):
        enabled_in_group = msg.chat and msg.chat.type == "supergroup" and msg.chat.id in self.bot.config['antibot']['group_ids']
        user_is_not_us = msg.from_user and msg.from_user.id != self.bot.uid
        has_date = msg.date

        # Lazily evalulate suspicious content as it is significantly more expensive
        if enabled_in_group and user_is_not_us and has_date:
            return self.msg_content_suspicious(msg)

        return False

    def take_action(self, msg):
        self.bot.client.send_message(msg.chat.id, f'/ban Spambot detected (ID: `{msg.from_user.id}`)', reply_to_message_id=msg.message_id)
        time.sleep(1)
        self.bot.client.delete_messages(msg.chat.id, msg.message_id)

        self.log_stat('spambots_banned')

    def on_message(self, msg):
        if self.msg_is_suspicious(msg):
            member = self.bot.client.get_chat_member(msg.chat.id, msg.from_user.id)
            if not member.date:
                return

            delta = msg.date - member.date
            if delta <= self.bot.config['antibot']['threshold_time']:
                # This is probably a spambot, take action against the user
                self.take_action(msg)

    @command.desc('Toggle the antibot auto-moderation feature in this group')
    def cmd_antibot(self, msg):
        if not msg.chat or msg.chat.type != "supergroup":
            return "__Antibot can only be used in supergroups.__"

        state = msg.chat.id in self.bot.config['antibot']['group_ids']
        state = not state

        if state:
            self.bot.config['antibot']['group_ids'].append(msg.chat.id)
        else:
            self.bot.config['antibot']['group_ids'].remove(msg.chat.id)
        self.bot.save_config()

        status = 'enabled' if state else 'disabled'
        return f'Antibot is now **{status}** in this group.'
