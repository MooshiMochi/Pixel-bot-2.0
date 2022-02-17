from discord.ext import commands

class TNError(Exception):
    pass

class Forbidden(TNError):
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

class RequiredEmojiNotFound(TNError):
    pass

class NotVerified(commands.CheckFailure):
    pass

class Verified(commands.CheckFailure):
    pass
