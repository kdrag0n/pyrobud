import asyncio
from datetime import timedelta, timezone
from typing import ClassVar, Union

import regex
import telethon as tg

from .. import command, module, util

MessageEvent = Union[tg.events.NewMessage.Event, tg.events.ChatAction.Event]

SUSPICIOUS_KEYWORDS = [
    "invest",
    "profit",
    "binance",
    "binanse",
    "bitcoin",
    "testnet",
    "bitmex",
    "wealth",
    "mytoken",
    "no scam",
    "legi",
    "trading",
    "binary option",
    "talk with you in private",
    "go_start",
    "s.tart",
    "cash out",
    "withdraw",
]

SUSPICIOUS_ENTITIES = [
    tg.tl.types.MessageEntityUrl,
    tg.tl.types.MessageEntityTextUrl,
    tg.tl.types.MessageEntityEmail,
    tg.tl.types.MessageEntityPhone,
    tg.tl.types.MessageEntityCashtag,
]

NORMAL_CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\"
OBFUSCATED_CHARSETS = [
    "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９～ ｀！＠＃＄％＾＆＊（）－＿＝＋［］｛｝|；：＇＂,＜．＞/？\\",
    "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ0①②③④⑤⑥⑦⑧⑨~ `!@#$%^&⊛()⊖_⊜⊕[]{}⦶;:'\",⧀⨀⧁⊘?⦸",
    "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩⓿123456789~ `!@#$%^&⊛()⊖_⊜⊕[]{}⦶;:'\",⧀⨀⧁⊘?⦸",
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "⒜⒝⒞⒟⒠⒡⒢⒣⒤⒥⒦⒧⒨⒩⒪⒫⒬⒭⒮⒯⒰⒱⒲⒳⒴⒵⒜⒝⒞⒟⒠⒡⒢⒣⒤⒥⒦⒧⒨⒩⒪⒫⒬⒭⒮⒯⒰⒱⒲⒳⒴⒵0⑴⑵⑶⑷⑸⑹⑺⑻⑼~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉0123456789~ `!@#$%^&⧆()⊟_=⊞[]{}|;:'\",<⊡>⧄?⧅",
    "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉0123456789~ `!@#$%^&*()-_=+[]{}|;:'\",<.>/?\\",
    "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz∀qƆpƎℲפHIſʞ˥WNOԀQɹS┴∩ΛMX⅄Z0ƖᄅƐㄣϛ9ㄥ86~ ,¡@#$%^⅋*)(-‾=+][}{|;:,,,'>˙</¿",
]
OBFUSCATED_TRANS_TABLES = [
    str.maketrans(NORMAL_CHARSET, charset) for charset in OBFUSCATED_CHARSETS
]

CHINESE_PATTERN = regex.compile(r".*\p{IsHan}.*", regex.UNICODE)


def decode_obfuscated_text(text: str):
    for trans in OBFUSCATED_TRANS_TABLES:
        text = text.translate(trans)

    return text


def msg_text_highly_suspicious(msg: tg.custom.Message):
    return (
        msg.entities
        and any(
            type(entity) == tg.tl.types.MessageEntityBold for entity in msg.entities
        )
        and CHINESE_PATTERN.match(msg.raw_text)
    )


class AntibotModule(module.Module):
    name: ClassVar[str] = "Antibot"
    db: util.db.AsyncDB
    group_db: util.db.AsyncDB
    user_db: util.db.AsyncDB

    async def on_load(self) -> None:
        self.db = self.bot.get_db("antibot")
        self.group_db = self.db.prefixed_db("groups.")
        self.user_db = self.db.prefixed_db("users.")

        # Migrate message tracking start times to the new per-group format
        fmsg_start_time = await self.db.get("first_msg_start_time")
        if fmsg_start_time is not None:
            self.log.info(
                "Migrating message tracking start times to the new per-group format"
            )

            async for key, value in self.group_db:
                if key.endswith(".enabled") and value:
                    await self.group_db.put(
                        key.replace(".enabled", ".enable_time"), fmsg_start_time
                    )

            await self.db.delete("first_msg_start_time")

    def msg_has_suspicious_entity(self, msg: tg.custom.Message) -> bool:
        if not msg.entities:
            return False

        # Messages containing certain entities are more likely to be spam
        return any(type(entity) in SUSPICIOUS_ENTITIES for entity in msg.entities)

    def msg_has_suspicious_keyword(self, msg: tg.custom.Message) -> bool:
        if not msg.raw_text:
            return False

        text = msg.raw_text
        # Include link preview content as well
        if msg.web_preview:
            webpage = msg.web_preview
            # Use a f-string so we don't need to deal with None values
            text += f"{webpage.site_name}{webpage.title}{webpage.description}"

        # Decode text with obfuscated characters
        text = decode_obfuscated_text(text)
        # Only check lowercase
        text = text.lower()

        # Many spam messages mention certain keywords, such as cryptocurrency exchanges
        return any(kw in text for kw in SUSPICIOUS_KEYWORDS)

    def msg_content_suspicious(self, msg: tg.custom.Message) -> bool:
        # Forwarded messages are subject to more aggressive entity checks
        suspicious_entity = self.msg_has_suspicious_entity(msg)
        if msg.forward and suspicious_entity:
            return True

        # All messages are subject to keyword checks
        if self.msg_has_suspicious_keyword(msg):
            return True

        # Messages with bold text, Chinese characters (in groups where English is the primary language), *and* suspicious entities
        if msg_text_highly_suspicious(msg) and suspicious_entity:
            return True

        # Allow otherwise
        return False

    @staticmethod
    def msg_type_suspicious(msg: tg.custom.Message) -> bool:
        return bool(msg.contact or msg.geo or msg.game)

    async def msg_data_is_suspicious(self, msg: tg.custom.Message) -> int:
        incoming = not msg.out
        has_date = msg.date
        forwarded = msg.forward

        # Message *could* be suspicious if we didn't send it
        # Check for a date to exonerate empty messages
        if incoming and has_date:
            # Lazily evaluate suspicious content as it is more expensive
            if forwarded:
                # Messages forwarded from a linked channel by Telegram don't have a sender
                # We can assume these messages are safe since only admins can link channels
                sender = await msg.get_sender()
                if sender is None:
                    return 0

                # Spambots don't forward their own messages; they mass-forward
                # messages from central coordinated channels for maximum efficiency
                # This protects users who forward questions with links/images to
                # various support chats asking for help (arguably, that's spammy,
                # but it's out of scope for this function)
                if (
                    msg.forward.from_id == sender.id
                    or msg.forward.from_name == tg.utils.get_display_name(sender)
                ):
                    return 0

            if self.msg_type_suspicious(msg) or self.msg_content_suspicious(msg):
                return 10
            elif msg.photo and (not msg.text or self.msg_has_suspicious_entity(msg)):
                return 5

        return 0

    async def msg_is_suspicious(self, msg: tg.custom.Message) -> bool:
        # Check if the data in the message is suspicious
        data_score = await self.msg_data_is_suspicious(msg)
        if data_score <= 0:
            return False

        # Load message metadata entities
        chat = await msg.get_chat()
        sender = await msg.get_sender()

        # Messages forwarded from a linked channel by Telegram don't have a sender
        # We can assume these messages are safe because only admins can link channels
        if sender is None:
            return False

        # Load group-specific user information
        try:
            ch_participant = await self.bot.client(
                tg.tl.functions.channels.GetParticipantRequest(chat, sender)
            )
        except (ValueError, tg.errors.UserNotParticipantError):
            # User was already banned or deleted; we don't need to proceed
            return False

        ptcp = ch_participant.participant

        # Exempt the group creator and admins
        if isinstance(ptcp, tg.tl.types.ChannelParticipantCreator) or isinstance(
            ptcp, tg.types.ChannelParticipantAdmin
        ):
            return False

        delta = msg.date - ptcp.date
        just_joined = delta.total_seconds() <= await self.db.get("threshold_time", 30)

        join_time_sec = int(ptcp.date.replace(tzinfo=timezone.utc).timestamp())
        first_msg_eligible = join_time_sec > await self.group_db.get(
            f"{msg.chat_id}.enable_time", 0
        )
        if first_msg_eligible:
            # We started tracking first messages in this group before the user
            # joined, so we can run the first message check
            is_first_msg = not await self.user_db.get(
                f"{sender.id}.has_spoken_in_{msg.chat_id}", False
            )
            if is_first_msg and data_score >= 10:
                # Suspicious message was the user's first message in this group
                return True

            # Less suspicious first messages sent right after joining also count
            if is_first_msg and just_joined and data_score >= 5:
                return True

        # Allow this message
        return False

    @staticmethod
    def profile_check_invite(user: tg.types.User) -> bool:
        # Some spammers have Telegram invite links in their first or last names
        return "t.me/" in tg.utils.get_display_name(user)

    async def user_is_suspicious(self, user: tg.types.User) -> bool:
        # Some spammers have invites in their names
        return self.profile_check_invite(user)

    async def take_action(self, event: MessageEvent, user: tg.types.User) -> None:
        # Wait a bit for welcome bots to react
        await asyncio.sleep(1)

        # Delete all of the sender's messages
        chat = await event.get_chat()
        request = tg.tl.functions.channels.DeleteUserHistoryRequest(chat, user)
        await self.bot.client(request)

        # Kick the sender
        await self.bot.client.kick_participant(chat, user)

        # Log the event
        self.log.info(f'Kicked spambot with ID {user.id} in group "{chat.title}"')
        await self.bot.log_stat("spambots_banned")

        # Delete the spam message just in case
        await event.delete()

    async def is_enabled(self, event: MessageEvent) -> bool:
        return bool(
            event.is_group
            and await self.group_db.get(f"{event.chat_id}.enabled", False)
        )

    async def on_message(self, msg: tg.events.NewMessage.Event) -> None:
        # Only run in groups where antibot is enabled
        if await self.is_enabled(msg):
            if await self.msg_is_suspicious(msg.message):
                # This is most likely a spambot, take action against the user
                user = await msg.get_sender()
                await self.take_action(msg, user)
            else:
                await self.user_db.put(
                    f"{msg.sender_id}.has_spoken_in_{msg.chat_id}", True
                )

    async def clear_group(self, group_id: int) -> None:
        async for key, _ in self.group_db.iterator(prefix=f"{group_id}."):
            await self.group_db.delete(key)

        async for key, _ in self.user_db:
            if key.endswith(f".has_spoken_in_{group_id}"):
                await self.user_db.delete(key)

    async def on_chat_action(self, action: tg.events.ChatAction.Event) -> None:
        # Remove has-spoken-in flag for departing users
        if (action.user_left or action.user_kicked) and await self.is_enabled(action):
            await self.user_db.delete(
                f"{action.user_id}.has_spoken_in_{action.chat_id}"
            )

            # Clean up antibot data if we left the group
            if action.user_id == self.bot.uid:
                self.log.info(f"Cleaning up settings for group {action.chat_id}")
                await self.clear_group(action.chat_id)

            return

        # Only filter new users
        if not (action.user_added or action.user_joined):
            return

        # Only act in groups where this is enabled
        if not await self.is_enabled(action):
            return

        # Fetch the user's data and run checks
        user = await action.get_user()
        if await self.user_is_suspicious(user):
            # This is most likely a spambot, take action against the user
            await self.take_action(action, user)

    @command.desc("Toggle the antibot auto-moderation feature in this group")
    async def cmd_antibot(self, ctx: command.Context) -> str:
        if not ctx.msg.is_group:
            return "__Antibot can only be used in groups.__"

        if not ctx.msg.is_channel:
            return "__Please convert this group to a supergroup in order to enable antibot.__"

        if ctx.input:
            state = ctx.input.lower() in util.INPUT_YES
        else:
            state = not await self.group_db.get(f"{ctx.msg.chat_id}.enabled", False)

        if state:
            # Check for required permissions
            chat = await ctx.msg.get_chat()
            ch_participant = await self.bot.client(
                tg.tl.functions.channels.GetParticipantRequest(chat, self.bot.user)
            )
            ptcp = ch_participant.participant

            if isinstance(ptcp, tg.types.ChannelParticipantCreator):
                # Group creator always has all permissions
                pass
            elif isinstance(ptcp, tg.types.ChannelParticipantAdmin):
                # Check for the required admin permissions
                if not (
                    ptcp.admin_rights.delete_messages and ptcp.admin_rights.ban_users
                ):
                    return "__Antibot requires the **Delete Messages** and **Ban Users** permissions.__"
            else:
                return "__I must be an admin with the **Delete Messages** and **Ban Users** permissions for antibot to work.__"

            await self.group_db.put(f"{ctx.msg.chat_id}.enabled", True)
            await self.group_db.put(f"{ctx.msg.chat_id}.enable_time", util.time.sec())
        else:
            await self.clear_group(ctx.msg.chat_id)

        status = "enabled" if state else "disabled"
        comment = (
            " Note that only __new__ users will be affected to reduce the risk of false positives."
            if state
            else ""
        )
        return f"Antibot is now **{status}** in this group.{comment}"
