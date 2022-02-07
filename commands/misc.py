from discord import Embed, Member
from discord.ext import commands

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from constants import const


class Miscellaneous(commands.Cog):
    def __init__(self, client):
        self.client = client

    
    @cog_slash(name="avatar", description="Show the avatar of a user", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The memebr to show the avatar picture of", option_type=6, required=False) | {"focused": True}
    ])
    async def avatar(self, ctx:SlashContext, member:Member=None):
        
        await ctx.defer(hidden=True)

        if not member:
            member = ctx.author

        em = Embed(title="Avatar", color=self.client.failure)
        em.set_author(name=f"{member.name}#{member.discriminator}", icon_url=member.avatar_url_as(static_format="png", size=4096))
        em.set_image(url=member.avatar_url_as(static_format="png", size=4096))
        await ctx.embed(embed=em, footer="Miscellaneous")


def setup(client):
    client.add_cog(Miscellaneous(client))
    