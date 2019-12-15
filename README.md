# Pyrobud

A clean selfbot for Telegram with an emphasis on quality and practicality.

Pyrobud is designed to complement the official clients, rather than replacing
them as many other selfbots tend to lean towards. It is written in Python using
the [Telethon](https://github.com/LonamiWebs/Telethon) library.

A working installation of **Python 3.6** or newer is required to run Pyrobud.

## Compatibility

Pyrobud should be compatible with all major operating systems. While it has not
been officially tested on Windows or macOS, there should not be anything
preventing it from working on those platforms. Please let me know if you've
gotten it working so I can add it here.

It is also possible to run the bot on a smartphone. On Android it can be done
with the [Termux](https://wiki.termux.com/wiki/Main_Page) app, and on iOS it
should be possible using the [iSH](https://ish.app/) app. Note that I have only
tested the Android solution, so try it on iOS at your own risk.

I do not endorse abuse of free cloud web hosting services (such as Heroku) to run
the bot. Please do not ask me for assistance with such endeavors — you are on
your own if you insist on running the bot that way.

## Installation

### Using Docker

Simply run `docker run --rm -v "$PWD/data:/data" kdrag0n/pyrobud` to run the
latest stable version with the data directory set to `data` in the current
working directory. Feel free to customize the data directory as you wish, as
long as you create `config.toml` in your chosen data directory using the
instructions below. The data section of the Docker command should always look
like `-v "/path/to/data:/data"`.

Note that the official Docker image only supports Linux x86_64. Other operating
systems and architectures are not supported. However, pull requests contributing
such support are welcome.

### Using `pip`

Run `pip3 install -r requirements.txt` to install all the dependencies. After
that, you can choose to either install the bot as a package using `pip3 install .`
and invoke it using the `pyrobud` command, or run the bot in-place (which is
described in the Usage section).

It is recommended to install everything inside a virtual environment to minimize
contamination of the system Python install, since many of the bot's dependencies
are not typically packaged by Linux distributions. Such environments can be
created easily using the following command: `python3 -m venv [target directory]`

They can then be activated using `source [target directory]/bin/activate` or the
equivalent command and script for your shell of choice.

You can still install all the dependencies in your system Python environment,
but please be aware of the potential issues when doing so. The installed packages
may conflict with the system package manager's installed packages, which can
cause trouble down the road and errors when upgrading conflicting packages.
**You have been warned.**

## Configuration

Copy `config.toml.sample` to `config.toml` and edit the settings as desired.
Each and every setting is documented by the comments above it.

Obtain the API ID and hash from [Telegram's website](https://my.telegram.org/apps).
**TREAT THESE SECRETS LIKE A PASSWORD!**

Configuration must be complete before starting the bot for the first time for it
to work properly.

## Usage

To start the bot, type `python3 main.py` if you are running it in-place or use
command corresponding to your chosen installation method above.

When asked for your phone number, it is important that you type out the **full**
phone number of your account, including the country code, without any symbols
such as spaces, hyphens, pluses, or parentheses. For example, the US number
`+1 (234) 567-8910` would be entered as `12345678910`. Any other format will be
rejected by Telegram.

After the bot has started, you can run the `help` command to view all the
available commands and modules. This can be done anywhere on Telegram as long as
you prepend the command prefix to the name of the command you wish to invoke.
The default prefix (if you haven't changed it in the config) is `.`, so one
would type `.help` to run the command. All other commands work the same way,
save for snippet replacements which are used with `/snipname/` anywhere in a
message.

## Support

Feel free to join the [official support group](https://t.me/pyrobud) on Telegram
for help or general discussion regarding the bot. You may also
[open an issue on GitHub](https://github.com/pyrobud/pyrobud/issues) for bugs,
suggestions, or anything else relevant to the project.
