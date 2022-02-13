from discord.ext import commands
from utils.exceptions import NotGuildOwner
from re import findall
from utils.exceptions import InvalidURLError

bool_args = {
    'y': True,
    'yes': True,
    'on': True,
    '1': True,
    'true': True,
    True: True,
    'n': False,
    'no': False,
    'off': False,
    '0': False,
    'false': False,
    False: False
}

class Converters:

    class Boolean(commands.Converter):
        async def convert(self, argument):
            if argument.lower() not in bool_args:
                raise commands.BadBoolArgument(argument)
            return bool_args[argument.lower()]


class Checks:

    def is_guild_owner():
        async def predicate(ctx):
            if ctx.guild.owner_id == ctx.author.id:
                return True
            raise NotGuildOwner(str(ctx.author))
        return commands.check(predicate)


class Other:
    @staticmethod
    def roleIsManaged(role):
        return role.is_default() or role.is_bot_managed() \
        or role.is_premium_subscriber() or role.is_integration()


class url:
    def __init__(self, link):

        if not link:
            raise ValueError("Could not convert '%s' to url" % link)
        else:
            check = findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", link)
            if check:
                link = str(link).replace(".webm", ".png")

                if not any([True for ext in [".jpg", "jpeg", ".png", ".gif"] if ext in str(link)]):

                    raise InvalidURLError("The url: '%s' is not valid." % link)
                else:
                    self.link = link
            else:
                raise InvalidURLError("The url: '%s' is not valid." % link)

    def __str__(self):
        return str(self.link)
