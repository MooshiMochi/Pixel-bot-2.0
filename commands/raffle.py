import json
import discord

from datetime import datetime

from random import sample

from main import MyClient

from discord.ext import commands, tasks
from discord.utils import sleep_until

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from constants import const

class Raffle(commands.Cog):
    def __init__(self, client):
        self.client:MyClient = client
    
        with open("data/raffle/raffles.json", "r") as f:
            self.raffles = json.load(f)

        self.getting_ready.start()

    @tasks.loop(count=1)
    async def getting_ready(self):
        for guild in self.client.guilds:
            guild = str(guild.id)
            if guild not in self.raffles.keys():
                self.raffles[guild] = {}
                continue

            if self.raffles[guild]:
                for key in self.raffles[guild].copy().keys():
                    self.client.loop.create_task(self.waiting_task(guild, key))


    @getting_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()

    
    async def waiting_task(self, guild_id:int, key:str):
        await self.client.wait_until_ready()

        ts = self.raffles[str(guild_id)][key]["scheduled_ts"]
        channel_id = int(key)

        guild:discord.Guild = self.client.get_guild(int(guild_id))
        
        winners = self.raffles[str(guild_id)][key]["winners"]

        if not guild:
            # Guild could not be found. Silently delete all guild raffles
            self.raffles.pop(str(guild_id), None)
            return

        channel:discord.TextChannel = guild.get_channel(channel_id)
        if not channel:
            # Channel could not be found. Silently cancel the raffle
            self.raffles[str(guild_id)].pop(key, None)
            return

        dt_ts = datetime.fromtimestamp(float(ts))
        
        await sleep_until(dt_ts)

        boost_users = []
        for mem in guild.members:
            for role in mem.roles:
                if role.is_premium_subscriber():
                    boost_users.append(mem)

        em = discord.Embed(title="Boosters' Raffle Results!", description="", color=self.client.failure)
        em.set_footer(text="TN | Raffle", icon_url=self.client.png)
        if not boost_users:
            em.description = "**No one has boosted the server. No winner was chosen 😿**"
            try:
                await channel.send(embed=em)
            except (discord.HTTPException, discord.Forbidden):
                pass
            
        elif len(boost_users) <= winners:
            em.description = "**__Winners:__**\n"
            for mem in boost_users:
                em.description += f"> - {mem.name}#{mem.discriminator}\n\n"
            
            try:
                await channel.send(embed=em)
            except (discord.HTTPException, discord.Forbidden):
                pass
            
        else:
            winners_li = sample(boost_users, winners)
            
            em.description = "**__Winners:__**\n"
            for mem in winners_li:
                em.description += f"> - {mem.name}#{mem.discriminator}\n\n"
            try:
                await channel.send(embed=em)
            except (discord.HTTPException, discord.Forbidden):
                pass

        self.raffles[str(guild_id)].pop(key, None)

        with open("data/raffle/raffles.json", "w") as f:
            json.dump(self.raffles, f, indent=2)
        return


    @cog_slash(name="raffle_schedule", description="[STAFF] Schedule a raffle for server boosters", guild_ids=const.slash_guild_ids, options=[
        create_option(name="winners", description="The number of winners to be chosen from the raffle", option_type=4, required=True),
        create_option(name="time", description="The date and time when the raffle will be held. Use the STRICT format 'DD/MM HH:MM'", option_type=3, required=True),
        create_option(name="channel", description="The channel where the raffle winners notification will be posted", option_type=7, required=True)
    ])
    @commands.has_permissions(manage_roles=True)
    async def raffle_schedule(self, ctx:SlashContext, winners:int=1, time:str=None, channel:discord.TextChannel=None):
        
        await self.client.wait_until_ready()

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("Param `channel` must be a Text Channel.", hidden=True)

        if winners <= 1:
            return await ctx.send("The minimum number of winners is 1.", hidden=True)
        
        elif winners > 5:
            return await ctx.send("The maximum number of winners is 5.", hidden=True)

        try:
            await channel.send("\u200b", delete_after=1)
        except (discord.HTTPException, discord.Forbidden):
            em = discord.Embed(description=f"I do not have enough permissions to\nsend messages in <#{channel.id}>", color=self.client.failure)
            em.set_footer(text="TN | Raffle", icon_url=self.client.png)
            return await ctx.send(embed=em, hidden=True)

        time_copy = time.strip()
        time = "2022/" + time.strip()

        scheduled_time = None
        
        try:
            scheduled_time = datetime.strptime(time, "%Y/%d/%m %H:%M")
        except ValueError:
            em = discord.Embed(description=f"Time data `{time_copy}` does not match the format specified in the command description.\nPlease check and try again.", color=self.client.failure)
            em.set_footer(text="TN | Raffle", icon_url=self.client.png)
            return await ctx.send(embed=em, hidden=True)

        
        self.raffles[str(ctx.guild_id)][str(channel.id)] = {
            "scheduled_ts": scheduled_time.timestamp(),
            "winners": winners
        }

        with open("data/raffle/raffles.json", "w") as f:
            json.dump(self.raffles, f, indent=2)
        
        em = discord.Embed(title="New raffle has been scheduled", description=f"Time:\n> <t:{int(scheduled_time.timestamp())}:R>\n\nChannel:\n> <#{channel.id}>\n\nNumber of winners:\n> {winners}", color=self.client.failure)
        em.set_footer(text="TN | Raffle", icon_url=self.client.png)

        self.client.loop.create_task(self.waiting_task(str(ctx.guild_id), str(channel.id)))

        return await ctx.send(embed=em, hidden=True)


def setup(client:MyClient):
    client.add_cog(Raffle(client))
