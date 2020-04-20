# Module Development Handbook

Want to make a module for an as-of-yet unimplemented feature that you desire?
Look no further! Pyrobud is **very extensible** and offers an easy-to-use module
API with first-class support for custom out-of-tree modules.

## Code Style

While not strictly necessary, it is **highly recommended** for custom modules to
follow the upstream [code style guidelines](https://github.com/kdrag0n/pyrobud/blob/master/CODE_STYLE.md).
It improves code readability dramatically, creates a unified standard style
followed by everyone in the project's community, and makes it easier for you to
upstream your code in the future should you decide to do so. There are really no
downsides to following the upstream code style in out-of-tree code.

## Creating the Class

All modules must subclass the core `module.Module` class (which provides some
basic facilities) in order to be detected and loaded. The name of the class does
not strictly matter, but setting it to something similar to the name of your
module is recommended for it to be easily identifiable while loading.

You should set a `name` class variable, which is a string that governs how your
module will show in the help command. The default name is `Unnamed`, but there
cannot be multiple modules with the same name so every module should have a
custom name set.

It is also possible to prevent a module from loading on startup by setting the
`disabled` class variable to `True`. Removing the variable or setting it to
`False` will reverse this behavior.

Instance variables should be declared below the class variables. While not
mandatory, it is good practice to declare them for type-checking purposes.

Example:

```python
# Import core components
from .. import module, util

# Subclass module.Module
class ExampleModule(module.Module):
    # Name (shows up in help)
    name = "Example"
    # Make sure you remove this or set it to False when developing your module!
    disabled = True

    # Database (instance variable)
    db: util.db.AsyncDB
```

## Default Instance Variables

There are some instance variables declared in the base `Module` class for
convenience that are available to all modules:

- `bot`: A reference to the `core.Bot` that this module is associated with
- `log`: A `logging.Logger` for the module's own logging, automatically named
  using the module name you set

Example usage:

```python
self.log.info(f"User ID: {self.bot.uid}")
```

## Database

The bot uses a key-value database backed by LevelDB (using the [`plyvel`](https://plyvel.readthedocs.io/en/latest/api.html)
library) as its data store. Modules should never use the central bot database
directly without a prefix; instead they should call `bot.get_db` to get a
prefixed slice of the database to operate on.

Example database usage:

```python
# Get prefixed database slice
self.db = self.bot.get_db("module_name")

# Perform operation
value = await self.db.get("current_value", 1)  # Default to 1
result = value * 9
await self.db.put("current_value", result)

# Increment operation counter
await self.db.inc("operations_performed")
```

## Event Handlers

You can subscribe to any event by defining a coroutine named `on_[event_name]`
in a module. Return values from event handlers are ignored.

### Telegram Events

There are several Telegram events available:

- [`message`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.newmessage.NewMessage)
- [`message_edit`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.messageedited.MessageEdited)
- [`message_delete`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.messagedeleted.MessageDeleted)
- [`message_read`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.messageread.MessageRead)
- [`chat_action`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.chataction.ChatAction)
- [`user_update`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.userupdate.UserUpdate)

All of them provide exactly one argument: the Telethon event object associated
with the event.

Below is an example of a simple message handler that logs the message and
increments a database counter:

```python
async def on_message(self, event: tg.events.NewMessage.Event) -> None:
    self.log.info(f"Received message: {event.message}")
    await self.db.inc("messages_received")
```

### Bot Events

There are several internal bot events that are not directly from Telegram:

- `load`
  - **Called when the module is loaded** so you can perform initialization
  - Initialization in `__init__` is discouraged because calling coroutines in it
    is impossible
  - This is called very early, *before* connecting to Telegram, so take care to
    not call any methods on the Telegram client
  - Note that the module must be **ready to go** after this event, since
    Telegram event listeners are registered *before* the start event is
    dispatched to prevent missed events
  - **Arguments:** none
- `start`
  - **Called when the bot is ready to go**, after connecting to Telegram and
    performing basic bookkeeping tasks such as fetching the user ID
  - Useful for performing initialization that requires calling Telegram
  - Called *before* catching up on events received during downtime, so performing
    most initialization here is safe
  - Telegram event handlers are registered *before* this event fires to prevent
    missed events, so the module's event handlers and commands
    **should still work** before this, albeit not at full potential
  - **Arguments:** current epoch time in microseconds
- `stop`
  - **Called when the bot is about to stop**
  - Cleanup work should be performed here
  - Most shared bot resources such as the HTTP client session and database are
    still available at this stage, but the
    **Telegram client will have been shut down** already
  - **Arguments:** none
- `stopped`
  - **Called after the bot has stopped**
  - All shared bot resources will have been closed
  - Useful for performing any last-minute work, such as late cleanup or restarting
  - This is the last coroutine that will be called before the event loop is shut down
  - **Arguments:** none
- `stat_event`
  - **Called when a stat event should be logged**
  - Usually only the Stats module listens for this event because it's responsible
    for incrementing the stat counters
  - Any module can dispatch this event using `bot.log_stat()`
  - **Arguments:** name of the event to log
    - This can be any arbitrary string from any module
    - If the Stats module is loaded, the counter will be available under the
      `stats.[event_name]` global database key
    - Examples: `spambots_banned`, `sent`, `received`, `stickers_created`
- `command`
  - **Called after a command has finished running successfully**
  - Failed commands will not dispatch this event
  - **Arguments:**
    - `command.Command` object describing the command that was invoked
    - [`telethon.events.NewMessage.Event`](https://telethon.readthedocs.io/en/latest/modules/events.html#telethon.events.newmessage.NewMessage.Event)
      object containing the message that invoked the command (same as the
      `message` event)

Below is an example of a `load` event handler:

```python
async def on_load(self) -> None:
    # Get prefixed database slice
    self.db = self.bot.get_db("example")

    # Perform database migration
    if await self.db.has("old_key"):
        old_value = await self.db.get("old_key")
        await self.db.put("new_key", old_value)
        await self.db.delete("old_key")
```

## Commands

While raw events are flexible, it is cumbersome to implement resilient and
sophisticated commands with them directly. To make simplify this common case,
the bot provides a full-fledged command system for modules to use.

Commands are just coroutines inside modules with a special naming pattern:
`cmd_[command_name]`. The module loader automatically derives the command name
from this.

Decorators are used to specify additional properties:

- **Description: `@command.desc("Command description")`**
- Aliases: `@command.alias("alias1", "alias2")`
- Usage: `@command.usage("[text to echo?, or reply]", optional=True, reply=True)`
  - This is a string shown to the user that describes how to use the command
  - `optional=True` means that this command can accept input but doesn't *require*
    it
    - If disabled *and* the usage decorator is present, the command will not be
      called if no input is given
  - `reply=True` means that this command can accept input from the replied-to message
    - If disabled, *only* arguments given in the invocation message itself will
      be accepted
    - For instance, calling a command with this *enabled* in a reply to a message
      that contains `x` and providing no arguments will cause the input to be set
      to `x` — the text from the replied-to message.

It is **highly recommended** for all commands to have concise descriptions as
they are shown to the user in the help command.

Commands can return a string as a shortcut for calling `ctx.respond` at the end:

```python
@command.desc("Simple echo/test command")
@command.alias("echotest", "test2")
@command.usage("[text to echo?, or reply]", optional=True, reply=True)
async def cmd_test(self, ctx: command.Context) -> str:
    # ctx.respond can still be used in commands that return strings as a means
    # of providing status updates, or anything that's not the final response
    await ctx.respond("Processing...")

    # Sleep 1 second here as a placeholder for "processing"
    await asyncio.sleep(1)

    # ctx.input includes input (if any) processed using the criteria specified
    # in the usage decorator
    if ctx.input:
        # Echo input text (i.e. arguments or replied-to message)
        return ctx.input
    else:
        # Return default message instead if no input is given
        return "It works!"
```

Not all commands return text, however, and some may need to pass additional
arguments to `ctx.respond`. If that happens to be the case, call `ctx.respond`
manually instead of returning a string. `ctx.respond` is flexible and supports
several different response modse, which can be specified using the `mode` keyword
argument:

- `edit`
  - Edits the invocation message with the response
- `reply`
  - Replies to the invocation message with the response
- `repost`
  - Deletes the invocation message and sends the response in reply to the same
    message the original one replied to

An example of this in a command that send media can be seen below:

```python
@command.desc("Get a random cat picture")
async def cmd_cat(self, ctx: command.Context) -> None:
    await ctx.respond("Fetching cat...")

    # Get a cat picture as a byte stream with a filename set
    # (calls an external HTTP API)
    cat_stream = await self.get_cat()

    # Respond with the cat picture
    # (repost mode is required because messages can't change types)
    await ctx.respond(file=cat_stream, mode="repost")
```

Often times, commands will need to perform relatively slow operations such as
making HTTP requests to external APIs, downloading data from Telegram, or even
responding to a message. If this is the case, providing status updates before
and after each operation is recommended to improve the user's perceived
interactivity. An example of this can be seen in the command above.

## Automatic Registration

You may have been wondering where the registration calls are.
**They don't exist** because everything is automatically probed and registered
during startup.

- **Modules** just need to be placed in the `modules` or `custom_modules`
  folders, known as "metamodules"
  - The metamodules take care of probing the modules
  - It is *possible* to define multiple modules in one file, but this is
    discouraged
  - Instead, you should create one file per module and the filename should be
    the name of the module in `snake_case`
- **Event handlers** just need to be defined as coroutines inside modules with
  the `on_event_name` naming pattern
  - The module loader takes care of probing and registering them
- **Events** do not need to be declared at all
  - The event dispatcher is flexible and allows events to be dispatched with any
    combination of name and arguments
  - The module loader also allows event handlers to subscribe to events with any
    name
- **Commands** just need to be defined as coroutines with the `cmd_command_name`
  naming pattern
  - They can also have decorators to specify other attributes, such as description
    (**highly recommended** for all commands), aliases, and usage
  - The module loader takes care of probing and registering them with the
    appropriate settings

## Location

Place all custom modules under the `custom_modules` folder rather than `modules`.
It helps avoid spamming automatic error reports about out-of-tree code to the
upstream project, and serves as visual separation so it's easy to locate custom
modules. Additionally, modules in `custom_modules` will not be tracked by Git so
updating the bot and contributing any core changes you may have in the future is
much easier.

## Licensing

You can license your custom modules however you want, but we recommend using the
MIT license because the upstream project uses it.

## Example Module

There is a functional example module located at [`custom_modules/example.py`](https://github.com/kdrag0n/pyrobud/blob/master/pyrobud/custom_modules/example.py)
which serves as a recap of this handbook as well as a template for your own
modules. It is disabled by default, but you can enable it by simply commenting
the `disabled = True` line near the top.

## Conclusion

This handbook and the example module should be very helpful for your module
development journey. However, they are by no means exhaustive. If you stumble
upon a roadblock not covered by these resources, feel free to
[open an issue on GitHub]([https://github.com/kdrag0n/pyrobud/issues/new](https://github.com/kdrag0n/pyrobud/issues/new)
or ask for help in [the support chat on Telegram](https://t.me/pyrobud).

Remember that there is also a comprehensive suite of modules included by default
in the "modules" folder. Please **refer to all of those** if you are confused
about something *before* you ask, since it saves everyone time in the end. Don't
be afraid to look through the bot core either — most parts are fairly well
commented, so they should not be too difficult to inspect.

**Good luck!**
