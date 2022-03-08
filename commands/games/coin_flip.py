
from discord.ext import commands

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from constants import const

class CoinFlip(commands.Cog):
    def __init__(self, client):
        self.client = client


    @cog_slash(name="coin_flip_challenge", description="Challenge someone to a coin flip duel", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The person to challenge", option_type=6, required=True)
    ])
    async def coin_flip_challenge(self, ctx: SlashContext):
        await ctx.defer(hidden=True)

        




def setup(client):
    client.add_cog(CoinFlip(client))