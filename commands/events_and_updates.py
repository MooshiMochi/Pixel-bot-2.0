import json
import discord
import asyncio

from discord import AllowedMentions
from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle

from datetime import datetime

from constants import const



class GuildEvents(commands.Cog):
    def __init__(self, client):
        self.client = client

        with open("data/events_and_updates/updates.json", "r") as f:
            self.updates = json.load(f)

        with open("data/events_and_updates/events.json", "r") as f:
            self.events = json.load(f)
    
        self.getting_ready.start()

    @tasks.loop(count=1)
    async def getting_ready(self):
        keys = self.updates.keys()
        keys2 = self.events.keys()
        tasks = []
        for guild in self.client.guilds:
            _id = str(guild.id)
            if _id not in keys:
                self.updates[_id] = {}
            elif self.updates[_id]:
                for key in self.updates[_id].keys():
                    tasks.append(self.create_sleeping_task(guild, key, "updates"))

            if _id not in keys2:
                self.events[_id] = {}
            elif self.events[_id]:
                for key in self.events[_id].keys():
                    tasks.append(self.create_sleeping_task(guild, key, "events"))
        
        self.save_data.start()
        if tasks:
            await asyncio.gather(*tasks)
    
    @tasks.loop(minutes=5.0)
    async def save_data(self):
        with open("data/events_and_updates/updates.json", "w") as f:
            json.dump(self.updates, f, indent=2)
            
        with open("data/events_and_updates/events.json", "w") as f:
            json.dump(self.events, f, indent=2)

    @getting_ready.before_loop
    @save_data.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()
    
    async def create_sleeping_task(self, guild:discord.Guild, task_key:str=None, _type:str=None):

        end_ts = float(task_key)
        curr = datetime.utcnow().timestamp()
        
        if _type == "updates":
            data = self.updates[str(guild.id)][task_key]
        elif _type == "events":
            data = self.events[str(guild.id)][task_key]
        
        if _type == "updates":
            em = discord.Embed(title=data["title"], description=data["desc"], color=self.client.failure)
        elif _type == "events":
            addon = ""
            if data["place_2_prize"]:
                addon += f"\n> **2nd place:** `{data['place_2_prize']}`"
            if data["place_3_prize"]:
                addon += f"\n> **3rd place:** `{data['place_3_prize']}`"
            
            if data['max_players']:
                addon += f"\n\n*Max players for this event are: `{data['max_players']}`*"

            em = discord.Embed(title=f'{data["event_name"]} event', description=f'This event will be hosted in {data["event_location"]} <t:{int(end_ts)}:R> with the following prize(s)\n> **1st place:** `{data["prize"]}`{addon}', color=self.client.failure)
        em.set_footer(text=f"TN | {_type.capitalize()}", icon_url=self.client.png)
        em.set_author(name=f"New {_type.capitalize()[:-1]}!", icon_url=self.client.png)


        send_settings = {
                "embed": em
            }
        if data["ping_role"]:
            send_settings["content"] = f"<@&{data['ping_role']}>"

        if curr < end_ts:
            await discord.utils.sleep_until(datetime.fromtimestamp(end_ts-600))
        
            
        ch = guild.get_channel(data['channel_id'])

        self.updates[str(guild.id)].pop(task_key, None) if _type == "updates" else self.events[str(guild.id)].pop(task_key, None) if _type == "events" else None

        role = guild.get_role(data['ping_role'])

        if not ch:
            await role.delete(reason=f"{_type.capitalize()[:-1]} has been sent. No longer needed")
            return

        try:
            await ch.send(**send_settings, allowed_mentions=AllowedMentions(roles=True))
            await asyncio.sleep(600)
        except (discord.Forbidden, discord.HTTPException):
            # Not enough permissions or channel not found. 
            pass
        await role.delete(reason=f"{_type.capitalize()[:-1]} has been sent. No longer needed")


    @cog_slash(name="event_create", description="Create an event with max players and a prize.", guild_ids=const.slash_guild_ids, options=[
        create_option(name="channel", description="The channel where the event will take place", option_type=7, required=True),
        create_option(name="event_name", description="The name of the event", option_type=3, required=True),
        create_option(name="event_location", description="The location where the event will be hosted in minecraft", option_type=3, required=True),
        create_option(name="prize", description="The prize the winnwer of the event will receieve", option_type=3, required=True),
        create_option(name="when", description="When to announce the update. Eg: 1d, 17h", option_type=3, required=True),
        create_option(name="ping_role_name", description="The name of the role that will be pinged with the announcement", option_type=3, required=True),
        create_option(name="role_color", description="The colour of the ping role", option_type=4, required=True, choices=[
            create_choice(value=0x1abc9c, name="Teal"),
            create_choice(value=0x2ecc71, name="Green"),
            create_choice(value=0x3498db, name="Blue"),
            create_choice(value=0x9b59b6, name="Purple"),
            create_choice(value=0xe91e63, name="Magenta"),
            create_choice(value=0xf1c40f, name="Gold"),
            create_choice(value=0xe67e22, name="Orange"),
            create_choice(value=0xe74c3c, name="Red"),
            create_choice(value=0x11806a, name="Dark Teal"),
            create_choice(value=0x1f8b4c, name="Dark Green"),
            create_choice(value=0x206694, name="Dark Blue"),
            create_choice(value=0x71368a, name="Dark Purple"),
            create_choice(value=0xad1457, name="Dark Magenta"),
            create_choice(value=0xc27c0e, name="Dark Gold"),
            create_choice(value=0xa84300, name="Dark Orange"),
            create_choice(value=0x992d22, name="Dark Red"),
            create_choice(value=0x607d8b, name="Dark Grey"),
            create_choice(value=0x979c9f, name="Light Grey"),
            create_choice(value=0x95a5a6, name="Lighter Grey"),
            create_choice(value=0x546e7a, name="Darker Grey"),
            create_choice(value=0x7289da, name="Blurple"),
            create_choice(value=0x99aab5, name="Greyple"),
            create_choice(value=0x36393F, name="Invisible")
        ]),
        create_option(name="place_2_prize", description="The prize for 2nd place in the event", option_type=3, required=False),
        create_option(name="place_3_prize", description="The prize for 3rd place in the event", option_type=3, required=False),
        create_option(name="max_players", description="The max number of players that can participate", option_type=4, required=False)
    ])
    @commands.has_permissions(administrator=True)
    async def event_create(self, ctx:SlashContext, channel:discord.TextChannel=None, event_name:str=None, event_location:str=None, prize:str=None, place_2_prize:str=None, place_3_prize:str=None, max_players:int=None, when:str=None, ping_role_name:str=None, role_color:int=None):
        await ctx.defer(hidden=True)

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send(f"Param `channel` must be a discord Text Channel", hidden=True)

        time = await self.client.format_duration(when)

        if time < 60 * 60:
            return await ctx.send("Minimum schedule time is 1 hour.", hidden=True)
        elif time > 30 * 24 * 60 * 60:
            return await ctx.send("Maximum schedule time is 30 days.", hidden=True)
        
        guild_id = str(ctx.guild_id)
        ts = datetime.utcnow().timestamp()
        
        if not place_2_prize and place_3_prize:
            place_2_prize, place_3_prize = place_3_prize, None

        new_role = await ctx.guild.create_role(name=ping_role_name, color=role_color, mentionable=False, reason="New Event Role")

        new_event = {
                "channel_id": channel.id,
                "strat": ts,
                "event_name": event_name,
                "event_location": event_location,
                "ping_role": new_role.id,
                "prize": prize,
                "place_2_prize": place_2_prize,
                "place_3_prize": place_3_prize,
                "max_players": max_players,
            }

        if guild_id not in self.updates.keys():
            self.events[guild_id]= {str(ts + time): new_event}
        else:
            self.events[guild_id][str(ts + time)] = new_event

        addon = ""
        if new_event["place_2_prize"]:
            addon += f"\n> **2nd place:** `{new_event['place_2_prize']}`"
        if new_event["place_3_prize"]:
            addon += f"\n> **3rd place:** `{new_event['place_3_prize']}`"
        
        if new_event['max_players']:
            addon += f"\n\n*Max players for this event are: `{new_event['max_players']}`*"

        em = discord.Embed(title=f'{new_event["event_name"]} event', description=f'This event will be hosted in {new_event["event_location"]} <t:{int(ts + time)}:R> with the following prize(s)\n> **1st place:** `{new_event["prize"]}`{addon}', color=self.client.failure)
        em.set_footer(text=f"TN | Events", icon_url=self.client.png)
        em.set_author(name=f"New Event!", icon_url=self.client.png)

        buttons = [create_button(
            label="Remind me",
            style=ButtonStyle.green,
            custom_id=f"events_{new_role.id}"
        )]
        ar = create_actionrow(*buttons)

        self.client.loop.create_task(self.create_sleeping_task(ctx.guild, str(ts + time), "events"))
        
        await channel.send(embed=em, components=[ar])
    
        await ctx.send(f"Event scheduled successfully! It will be posted in {channel.mention}.", hidden=True)
        return
        

    @cog_slash(name="update_create", description="Schedule an update notification.", guild_ids=const.slash_guild_ids, options=[
        create_option(name="channel", description="The channel where the update will be sent", option_type=7, required=True),
        create_option(name="title", description="The title of the event", option_type=3, required=True),
        create_option(name="desc", description="The description of the event", option_type=3, required=True),
        create_option(name="when", description="When to announce the update. Eg: 1d, 17h", option_type=3, required=True),
        create_option(name="ping_role_name", description="The name of the role that will be pinged with the announcement", option_type=3, required=True),
        create_option(name="role_color", description="The colour of the ping role", option_type=4, required=True, choices=[
            create_choice(value=0x1abc9c, name="Teal"),
            create_choice(value=0x2ecc71, name="Green"),
            create_choice(value=0x3498db, name="Blue"),
            create_choice(value=0x9b59b6, name="Purple"),
            create_choice(value=0xe91e63, name="Magenta"),
            create_choice(value=0xf1c40f, name="Gold"),
            create_choice(value=0xe67e22, name="Orange"),
            create_choice(value=0xe74c3c, name="Red"),
            create_choice(value=0x11806a, name="Dark Teal"),
            create_choice(value=0x1f8b4c, name="Dark Green"),
            create_choice(value=0x206694, name="Dark Blue"),
            create_choice(value=0x71368a, name="Dark Purple"),
            create_choice(value=0xad1457, name="Dark Magenta"),
            create_choice(value=0xc27c0e, name="Dark Gold"),
            create_choice(value=0xa84300, name="Dark Orange"),
            create_choice(value=0x992d22, name="Dark Red"),
            create_choice(value=0x607d8b, name="Dark Grey"),
            create_choice(value=0x979c9f, name="Light Grey"),
            create_choice(value=0x95a5a6, name="Lighter Grey"),
            create_choice(value=0x546e7a, name="Darker Grey"),
            create_choice(value=0x7289da, name="Blurple"),
            create_choice(value=0x99aab5, name="Greyple"),
            create_choice(value=0x36393F, name="Invisible")
        ])
    ])
    @commands.has_permissions(administrator=True)
    async def update_create(self, ctx:SlashContext, channel:discord.TextChannel=None, title:str=None, desc:str=None, when:str=None, ping_role_name:str=None, role_color:int=None):
        await ctx.defer(hidden=True)

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send(f"Param `channel` must be a discord Text Channel", hidden=True)

        time = await self.client.format_duration(when)

        if time < 60 * 60:
            return await ctx.send("Minimum schedule time is 1 hour.", hidden=True)
        elif time > 30 * 24 * 60 * 60:
            return await ctx.send("Maximum schedule time is 30 days.", hidden=True)
        
        guild_id = str(ctx.guild_id)
        ts = datetime.utcnow().timestamp()

        new_role = await ctx.guild.create_role(name=ping_role_name, color=role_color, mentionable=False, reason="New Update Role")

        new_update = {
                "channel_id": channel.id,
                "strat": ts,
                "title": title,
                "desc": desc,
                "ping_role": new_role.id
            }

        if guild_id not in self.updates.keys():
            self.updates[guild_id]= {str(ts + time): new_update}
        else:
            self.updates[guild_id][str(ts + time)] = new_update

        em = discord.Embed(title=new_update["title"], description=str(new_update["desc"]) + f"\n\nThis update will take place <t:{int(ts + time)}:R>", color=self.client.failure)
        em.set_footer(text=f"TN | Updates", icon_url=self.client.png)
        em.set_author(name=f"New Update!", icon_url=self.client.png)

        buttons = [create_button(
            label="Remind me",
            style=ButtonStyle.green,
            custom_id=f"updates_{new_role.id}"
        )]
        ar = create_actionrow(*buttons)

        self.client.loop.create_task(self.create_sleeping_task(ctx.guild, str(ts + time), "updates"))
        
        await channel.send(embed=em, components=[ar])
    
        await ctx.send(f"Update scheduled successfully! It will be posted in {channel.mention}.", hidden=True)
        return

    @commands.Cog.listener()
    async def on_component(self, ctx:ComponentContext):
        if str(ctx.custom_id).startswith("updates_") or str(ctx.custom_id).startswith("events_"):
            role_id = int(str(ctx.custom_id).replace("updates_", "").replace("events_", ""))
            role = ctx.guild.get_role(role_id)
            if str(ctx.custom_id).startswith("updates_"):
                    _type = "update"
            else:
                _type = "event"

            if role not in ctx.author.roles:
                try:
                    await ctx.author.add_roles(role)
                except AttributeError:
                    # button was probably clicked very late so we will ignore
                    return
                

                await ctx.send(f"You will get pinged 10 mins before this {_type}!", hidden=True)
            else:
                await ctx.send(f"Already got you on the list of users to ping 10 mins before the {_type}!", hidden=True)


def setup(client):
    client.add_cog(GuildEvents(client))
