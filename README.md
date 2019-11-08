# Pyrobud

A Telegram selfbot written in Python using [Telethon](https://github.com/LonamiWebs/Telethon).

**Python 3.6+** is required.

# Installation
Simply run `pip3 install -r requirements.txt`. This installs all the dependencies.

# Usage
Copy `config.toml.sample` to `config.toml` and edit the settings as desired.
Obtain the API ID and hash from [Telegram's website](https://my.telegram.org/apps).
**KEEP THIS SECRET!**

To start the bot, type `python3 main.py`.

Run the `help` command to view all the available commands and modules. This can
be done anywhere on Telegram as long as you prepend the command prefix to the
command name. The default prefix (if you haven't changed it in the config) is
`.`, so you would type `.help` to run the command. All other commands work the
same way, save for snippet replacements which are used with `/snipname/`
anywhere in a message.
