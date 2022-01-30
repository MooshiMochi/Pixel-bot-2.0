from discord.ext import commands
from utils.exceptions import NotGuildOwner

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
