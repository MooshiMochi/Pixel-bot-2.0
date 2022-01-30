import discord

from discord.ext import commands


class WhackASteve(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client


    


def setup(client):
    client.add_cog(WhackASteve(client=client))
