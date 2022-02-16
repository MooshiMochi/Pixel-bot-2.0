from discord.ext import commands

class PixelError(Exception):
    pass

class Forbidden(PixelError):
    pass

class BadPlayerArgument(commands.BadArgument):
    pass

class NotMod(commands.CheckFailure):
    pass

class NotAdmin(commands.CheckFailure):
    pass

class NotGuildOwner(commands.CheckFailure):
    pass

class NotBotSetOwner(commands.CheckFailure):
    pass

class InvalidURLError(commands.CheckFailure):
    pass

class RequiredEmojiNotFound(PixelError):
    pass
