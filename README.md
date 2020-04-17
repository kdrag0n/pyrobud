<p align="center">
    <img width="200" height="200" src="https://raw.githubusercontent.com/kdrag0n/pyrobud/master/assets/logo.png">
</p>

<h1 align="center">Pyrobud</h1>

<p align="center">
    <a href="https://github.com/kdrag0n/pyrobud/releases"><img src="https://img.shields.io/github/v/tag/kdrag0n/pyrobud?sort=semver" alt="Latest tag"></a>
    <a href="https://github.com/kdrag0n/pyrobud/actions?query=workflow%3A%22Build+%26+publish+Docker+image%22"><img src="https://img.shields.io/github/workflow/status/kdrag0n/pyrobud/Build%20%26%20publish%20Docker%20image" alt="CI status"></a>
    <a href="https://t.me/pyrobud"><img src="https://img.shields.io/badge/chat-on%20telegram-blueviolet" alt="Telegram chat"></a>
</p>

Pyrobud is a clean selfbot for Telegram with an emphasis on quality and
practicality.

It's designed to complement the official clients rather than replace them as
many other selfbots tend to lean towards. It is written in Python using
the [Telethon](https://github.com/LonamiWebs/Telethon) library.

A working installation of **Python 3.6** or newer is required to run Pyrobud.

## Compatibility

Pyrobud should be compatible with all major operating systems. While it has not
been officially tested on Windows or macOS, there should not be anything
preventing it from working on those platforms. Please let me know if you've
gotten it working so I can add it here.

It is also possible to run the bot on a smartphone. On Android it can be done
with the [Termux](https://wiki.termux.com/wiki/Main_Page) app, and on iOS it
should be possible using the [iSH](https://ish.app/) app.

## Installation

### Native dependencies

Pyrobud uses the native LevelDB library for its database, so you'll need to
install that first. Below are instructions for some common operating systems:

| OS/Distro    | Command                      |
| ------------ | ---------------------------- |
| Arch Linux   | `pacman -S leveldb`          |
| Ubuntu       | `apt install libleveldb-dev` |
| macOS        | `brew install leveldb`       |
| Termux       | `apt install leveldb`        |
| FreeBSD      | `pkg install leveldb`        |

### Using Docker

Simply run `docker run --rm -itv "$PWD/data:/data" kdrag0n/pyrobud` to run the
latest stable version with the data directory set to `data` in the current
working directory. Feel free to customize the data directory as you wish, as
long as you create `config.toml` in your chosen data directory using the
instructions below. The data section of the Docker command should always look
like `-v "/path/to/data:/data"`.

Note that the official Docker image only supports Linux x86_64. Other operating
systems and architectures are not supported. However, pull requests contributing
such support are welcome.

### Using pip

Run `python3 -m pip install .` to install the bot along with all of its dependencies. After
that, you can choose to either invoke it using the `pyrobud` command, or run the bot
in-place (which is described later in the Usage section).

It is highly recommended to install everything inside a virtual environment to
minimize contamination of the system Python install, since many of the bot's
dependencies are not typically packaged by Linux distributions. Such environments
can easily be created using the following command: `python3 -m venv [target directory]`

They can then be activated using `source [target directory]/bin/activate` or the
equivalent command and script for your shell of choice.

You can still install all the dependencies in your system Python environment,
but please be aware of the potential issues when doing so. The installed packages
may conflict with the system package manager's installed packages, which can
cause trouble down the road and errors when upgrading conflicting packages.
**You have been warned.**

#### Error: `Directory '.' is not installable. File 'setup.py' not found.`

This common error is caused by an outdated version of pip. We use the Poetry
package manager to make things easier to maintain, which works with pip through
PEP-517. This is a relatively new standard, so a newer version of pip is necessary
to make it work.

Upgrade to pip 19 to fix this issue: `pip3 install -U pip`

## Configuration

Copy `config.example.toml` to `config.toml` and edit the settings as desired.
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

## Deployment

For long-term server deployments, an example systemd service is available
[here](https://github.com/kdrag0n/pyrobud/blob/master/systemd/pyrobud.service).
It is strongly recommended to use this service for any long-term deployments as
it it includes parameters to improve security and restrict the system resources
the bot can utilize to limit damage if something goes awry. The example assumes
that the bot will run under an independent user named `pyrobud` with a virtual
environment located at `/home/pyrobud/venv` and a Git clone of the bot located
at `/home/pyrobud/pyrobud`. This setup avoids tainting the system's Python install
with unmanaged packages and allows the bot to self-update using Git.

If you're using Docker to run the bot, use [pyrobud-docker.service](https://github.com/kdrag0n/pyrobud/blob/master/systemd/pyrobud-docker.service)
instead.

`tmux` or `screen` should never be used to run the bot in production. A supervisor,
unlike a terminal multiplexer, contains a plethora of features crucial for proper
deployments: automatic ratelimited restarting, logging, monitoring, and more. Some,
such as systemd, also support limiting resources and and imposing restrictions for
security. A shell script that invokes Python in a `while` loop is not a replacement
for a proper supervisor.

## Contributing

See the [Contribution Guidelines](https://github.com/kdrag0n/pyrobud/blob/master/CONTRIBUTING.md)
for more information.

## Module Development

You can easily develop custom modules! See the
[Module Development Handbook](https://github.com/kdrag0n/pyrobud/blob/master/DEVELOPMENT.md)
for more information.

## Support

Feel free to join the [official support group](https://t.me/pyrobud) on Telegram
for help or general discussion regarding the bot. You may also
[open an issue on GitHub](https://github.com/pyrobud/pyrobud/issues) for bugs,
suggestions, or anything else relevant to the project.
