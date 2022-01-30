from logging import LoggerAdapter
from turtle import update
import discord
import json

from discord.ext import commands, tasks


class LeaderboardCommands(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.update_leaderboards.start()


    @tasks.loop(minutes=1.0)
    async def update_leaderboards(self):

        with open("data/level_system/chatlb.json", "w") as f:
            json.dump(self.client.chatlb, f, indent=2)
    
    @update_leaderboards.before_loop
    async def before_update_leaderboards(self):
        await self.client.wait_until_ready()


def setup(client):
    client.add_cog(LeaderboardCommands(client))