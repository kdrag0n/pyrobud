# Contribution Guidelines

**Don't be afraid to contribute your modules and/or features!** It is our goal
to reduce divergence and unify everything as much as possible, since a centralized
bot platform facilitates support and ease-of-use. However, we abide by some strict
policies upstream to keep quality under control.

Below are the policies we enforce. If your contribution meets all of these
requirements, feel free to [create a pull request](https://github.com/kdrag0n/pyrobud/compare)!

## Code Style

All contributions must adhere to the [code style guidelines](https://github.com/kdrag0n/pyrobud/blob/master/CODE_STYLE.md).
These are mostly enforced by our pre-commit hooks, which are [documented in the guidelines](https://github.com/kdrag0n/pyrobud/blob/master/CODE_STYLE.md#pre-commit-hooks).

## Functionality

Incomplete or half-baked contributions will not be accepted. Make sure that your
code is complete and has undergone thorough testing before submitting it.

## Type Checking

All contributions must contain full type annotations on all functions, including
those without return values. The code must also successfully type-check using the
[mypy](https://github.com/python/mypy) type checker. This is enforced by our
pre-commit hooks, which are [documented in the code style guidelines](https://github.com/kdrag0n/pyrobud/blob/master/CODE_STYLE.md#pre-commit-hooks).

## Redundancy and Bloat

Anything deemed **redundant** (i.e. already implemented to the same degree by
Telegram clients) will not be accepted. This is counteractive to the majority of
the other bots out there, but in the long run it helps keep this bot free of
bloat and improves the overall user experience. For example, a command to simply
kick a user will not be accepted because it is easier and more intuitive to
perform from a Telegram client. Features must be beneficial to the user.

Thus, you should not be discouraged if your contribution is rejected — you're
free to keep maintaining your features out-of-tree as a custom module. We ask,
however, that you refrain from modifying the core and utility code to keep
everything together — our goal is for all modules to work on all instances with
no code changes required.

## Licensing

All contributions will inherit the license of the upstream project, which is the MIT license.
