import telethon as tg

import command
import module


class AntibotModule(module.Module):
    name = 'Antibot'

    suspicious_keywords = [
        'investment',
        'profit',
        'binance',
        'binanse',
        'bitcoin',
        'testnet',
        'bitmex'
    ]

    suspicious_entities = [
        tg.types.MessageEntityUrl,
        tg.types.MessageEntityTextUrl,
        tg.types.MessageEntityEmail,
        tg.types.MessageEntityPhone
    ]

    async def on_load(self):
        # Populate config if necessary
        if 'antibot' not in self.bot.config:
            self.bot.config['antibot'] = {
                'threshold_time': 30,
                'group_ids': []
            }
        else:
            if 'threshold_time' not in self.bot.config['antibot']:
                self.bot.config['antibot']['threshold_time'] = 30 # seconds
            if 'group_ids' not in self.bot.config['antibot']:
                self.bot.config['antibot']['group_ids'] = []

    def msg_has_suspicious_entity(self, msg):
        if not msg.entities:
            return False

        # Messages containing certain entities are more likely to be spam
        for entity in msg.entities:
            if entity.__class__ in self.__class__.suspicious_entities:
                return True

        return False

    def msg_has_suspicious_keyword(self, msg):
        if not msg.raw_text:
            return False

        # Many spam messages mention certain keywords, such as cryptocurrency exchanges
        l_text = msg.raw_text.lower()
        for kw in self.__class__.suspicious_keywords:
            if kw in l_text:
                return True

        return False

    def msg_content_suspicious(self, msg):
        # Consolidate message content checks
        return self.msg_has_suspicious_entity(msg) or self.msg_has_suspicious_keyword(msg)

    def msg_data_is_suspicious(self, msg):
        incoming = not msg.out
        has_date = msg.date
        forwarded = msg.forward

        # Message *could* be suspicious if we didn't send it
        # Check for a date to exonerate empty messages
        if incoming and has_date:
            # Lazily evalulate suspicious content as it is more expensive
            return forwarded or self.msg_content_suspicious(msg)

        return False

    async def msg_is_suspicious(self, msg):
        # Check if the data in the message is suspicious
        if not self.msg_data_is_suspicious(msg):
            return False

        # Load group-specific user information
        chat = await msg.get_chat()
        sender = await msg.get_sender()
        ch_participant = await self.bot.client(tg.tl.functions.channels.GetParticipantRequest(chat, sender))
        participant = ch_participant.participant

        # Exempt the group creator
        if isinstance(participant, tg.tl.types.ChannelParticipantCreator):
            return False

        delta = msg.date - participant.date
        if delta.total_seconds() <= self.bot.config['antibot']['threshold_time']:
            # Suspicious message was sent shortly after joining
            return True

        # Allow this message
        return False

    async def take_action(self, msg):
        # Ban the sender
        chat = await msg.get_chat()
        sender = await msg.get_sender()
        rights = tg.tl.types.ChatBannedRights(until_date=None, view_messages=True)
        ban_request = tg.tl.functions.channels.EditBannedRequest(chat, sender, rights)
        await self.bot.client(ban_request)

        # Log the event
        print(f'NOTICE: banned spambot with ID {sender.id} in group "{chat.title}"')
        await msg.reply(f'❯❯ **Banned spambot** with ID `{sender.id}`')
        self.bot.dispatch_event_nowait('stat_event', 'spambots_banned')

        # Delete the spam message
        await msg.delete()

    async def on_message(self, msg):
        enabled_in_chat = msg.is_group and msg.chat_id in self.bot.config['antibot']['group_ids']

        if enabled_in_chat and await self.msg_is_suspicious(msg):
            # This is most likely a spambot, take action against the user
            await self.take_action(msg)

    @command.desc('Toggle the antibot auto-moderation feature in this group')
    async def cmd_antibot(self, msg):
        if not msg.is_group:
            return "__Antibot can only be used in groups.__"

        gid_table = self.bot.config['antibot']['group_ids']
        state = msg.chat_id in gid_table
        state = not state

        if state:
            gid_table.append(msg.chat_id)
        else:
            gid_table.remove(msg.chat_id)

        await self.bot.save_config()

        status = 'enabled' if state else 'disabled'
        return f'Antibot is now **{status}** in this group.'
