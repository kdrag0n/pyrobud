import telethon as tg
from util import add_lrm

def PrintChat(chat : tg.types.Chat):
    return f"\"{chat.title}\" ({chat.id})"

def PrintUser(user : tg.types.User):
    result = ""
    if (user.first_name or user.last_name):
        result += "\""
        if user.first_name: result += {user.first_name}
        if user.first_name and user.last_name: result += " "
        if user.last_name: result += {user.last_name}
        result += "\" "
    if (user.username): result += f"@{user.username} "
    if (user.id): result += f"(`{user.id})`"
    return result

tg.types.Chat.__str__ = PrintChat
tg.types.User.__str__ = PrintUser
