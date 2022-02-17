import asyncio
import json
import discord

from discord.ext import commands, tasks

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.model import BucketType

from datetime import datetime

from constants import const

class Counter(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        with open("data/counters/counter_config.json", "r") as f:
            self.config = json.load(f)

        with open("data/counters/counters.json", "r") as f:
            self.counters = json.load(f)

        self.categories = {}

        self.get_ready.start()

    @tasks.loop(count=1)
    async def get_ready(self):
        guilds = {}
        for guild in self.client.guilds:
            _id = str(guild.id)
            guilds[_id] = guild
            if _id not in self.config.keys():
                self.config[_id] = {"category_id": 0}
            elif "category_id" not in self.config[_id].keys():
                self.config[_id]["category_id"] = 0
            elif self.config[_id]["category_id"]:
                self.categories[_id] = guild.get_channel(self.config[_id]["category_id"])

            if _id not in self.counters.keys():
                self.counters[_id] = {}

        tasks = []
        if self.counters:
            for key, val in self.counters.items():
                if not val:
                    continue
                else:
                    for _key in val.keys():
                        tasks.append(self.sleeping_func(guilds[key], _key))
        if tasks:
            await asyncio.gather(*tasks)


    async def sleeping_func(self, guild:discord.Guild=None, key:str=None):
        while not self.counters[str(guild.id)][key]["finished"]:
            addon = 0
            total_days = ((self.counters[str(guild.id)][key]["end"] + 600) - self.counters[str(guild.id)][key]["start"]) // (24 * 60 * 60)
            days_passed = 0
            start = self.counters[str(guild.id)][key]["start"]
            if datetime.utcnow().timestamp() >= self.counters[str(guild.id)][key]["end"]:
                self.counters[str(guild.id)][key]["finished"] = True
                ch = guild.get_channel(int(key))
                if not ch:
                    self.counters[str(guild.id)].pop(key, None)
                    return
                name = str(ch.name).split("in:")[0].strip()
                await ch.edit(name=f"{name}: Now!")
                return

            while True:
                if datetime.utcnow().timestamp() < start + addon:
                    break
                else:
                    addon += 24 * 60 * 60
                
                if addon > 24 * 60 * 60:
                    days_passed += 1

            await discord.utils.sleep_until(datetime.fromtimestamp(start+addon))

            ch = guild.get_channel(int(key))
            if not ch:
                return
            name = str(ch.name).split("|")[0].strip()

            await ch.edit(name=f"{name} in: {int(total_days - days_passed)}d")
        
        self.counters[str(guild.id)].pop(key, None)
        return

    @cog_slash(name="config_counter", description="[STAFF] Configure the counter extension", guild_ids=const.slash_guild_ids, options=[
        create_option(name="category", description="Set the counter category where the VC's will be created", option_type=7, required=True)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def config_counter(self, ctx:SlashContext, category:discord.CategoryChannel=None):
        await ctx.defer(hidden=True)

        if not isinstance(category, discord.CategoryChannel):
            return await ctx.send("Param `category` must be a CategoryChannel type.", hidden=True)
        
        if str(ctx.guild_id) not in self.config.keys():
            self.config[str(ctx.guild_id)] = {"category_id": category.id}
        else:
            self.config[str(ctx.guild_id)]["category_id"] = category.id
        
        self.categories[str(ctx.guild_id)] = category

        with open("data/counters/counter_config.json", "w") as f:
            json.dump(self.config, f, indent=2)

        return await ctx.send(f"Set new counter category to {category.mention}", hidden=True)


    @cog_slash(name="counter_add", description="[STAFF] Add a counter VC", guild_ids=const.slash_guild_ids, options=[
        create_option(name="name", description="The name of the VC", option_type=3, required=True),
        create_option(name="days", description="The days to count", option_type=4, required=True)
    ])        
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 600, BucketType.guild)
    async def counter_add(self, ctx:SlashContext, name:str=None, days:int=None):
        await ctx.defer(hidden=True)

        if str(ctx.guild_id) not in self.config.keys():
            return await ctx.send("This counter commands are not configured for this guild yet. Use `/config_counter` to get started!", hidden=True)
        
        elif "category_id" not in self.config[str(ctx.guild_id)].keys():
            return await ctx.send("The counter channel category has not been set for this guild. Use `/config_counter` to get started!", hidden=True)

        if days <= 1:
            return await ctx.send("The counter must be created at least 2 days in advance!", hidden=True)
        
        if days >= 30:
            return await ctx.send("Param `days` cannot be greater than 30 days.", hidden=True)

        bot_top_role = ctx.guild.roles.index(ctx.guild.me.top_role)
        all_roles = ctx.guild.roles
        overwrites = {role: discord.PermissionOverwrite(connect=False) for role in ctx.guild.roles if all_roles.index(role) < bot_top_role}
        overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(connect=False)
                
        channel = await ctx.guild.create_voice_channel(name=f"{name} in: {int(days)}d", 
        overwrites=overwrites)

        self.counters[str(ctx.guild_id)][str(channel.id)] = {"end": datetime.utcnow().timestamp() + (days * 24 * 60 * 60), "start": datetime.utcnow().timestamp(), "finished": False}

        with open("data/counters/counters.json", "w") as f:
            json.dump(self.counters, f, indent=2)

        await self.client.loop.create_task(self.sleeping_func(ctx.guild, str(channel.id)))

        return await ctx.send(f"New counter VC created: {channel.mention}")

    
    @cog_slash(name="counter_change", description="[STAFF] Edit the name or days of a counter", guild_ids=const.slash_guild_ids, options=[
        create_option(name="vc_id", description="The ID of the voice channel", option_type=3, required=True),
        create_option(name="new_name", description="The new name of the counter", option_type=3, required=False),
        create_option(name="new_days", description="New amount of days to count down for", option_type=4, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 600, BucketType.guild)
    async def counter_change(self, ctx:SlashContext, vc_id:str=None, new_name:str=None, new_days:str=None):
        await ctx.defer(hidden=True)

        if not str(ctx.guild_id) in self.counters.keys():
            return await ctx.send("This counter commands are not configured for this guild yet. Use `/config_counter` to get started!", hidden=True)
        
        counter = self.counters[str(ctx.guild_id)].get(vc_id, None)

        if not counter:
            return await ctx.send("Could not find that counter. Please check and try again!", hidden=True)

        if not new_days and not new_name:
            return await ctx.send("No changes were made to the counter.", hidden=True)
        
        try:
            ch = ctx.guild.get_channel(int(vc_id))
        except ValueError:
            return await ctx.send("Invalid VC ID was provided. It must be a number!", hidden=True)

        if not ch:
            self.counters[str(ctx.guild_id)].pop(vc_id, None)
            return await ctx.send("It appears that the counter has been deleted. Please start a new one using `/counter_add`.", hidden=True)

        if new_name:
            time = str(ch.name).split("in:")[1].strip()
            await ch.edit(name=f"{new_name} in: {time}")

        elif new_days:
            if new_days <= 1:
                return await ctx.send("The counter must be created at least 2 days in advance!", hidden=True)
            
            if new_days >= 30:
                return await ctx.send("Param `days` cannot be greater than 30 days.", hidden=True)

            name = str(ch.name).split("in:")[0].strip()
            await ch.edit(name=f"{name} in: {int(new_days)}d")

        with open("data/counters/counters.json", "w") as f:
            json.dump(self.counters, f, indent=2)

        return await ctx.send(f"Counter edited!\n> Name: `{new_name if new_name else 'unchanged'}`\n> Counting Days: `{new_days if new_days else 'unchagned'}`", hidden=True)

    
    @cog_slash(name="counter_remove", description="[STAFF] Delete a counter", guild_ids=const.slash_guild_ids, options=[
        create_option(name="vc_id", description="The ID of the Voice Channel", option_type=3, required=True)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 600, BucketType.guild)
    async def counter_remove(self, ctx:SlashContext, vc_id:str=None):
        await ctx.defer(hidden=True)

        if not str(ctx.guild_id) in self.counters.keys():
            return await ctx.send("This counter commands are not configured for this guild yet. Use `/config_counter` to get started!", hidden=True)
        
        counter = self.counters[str(ctx.guild_id)].get(vc_id, None)

        if not counter:
            return await ctx.send("Could not find that counter. Please check and try again!", hidden=True)
        
        self.counters[str(ctx.guild_id)].pop(vc_id, None)

        with open("data/counters/counters.json", "w") as f:
            json.dump(self.counters, f, indent=2)

        return await ctx.send(f"Counter `{vc_id}` deleted successfully!", hidden=True)


    @get_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(Counter(client))
