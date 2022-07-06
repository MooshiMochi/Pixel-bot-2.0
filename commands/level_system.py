import asyncio
import discord
import json

from discord.ext import commands, tasks

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from datetime import datetime

from constants import const


class LevelSystem(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.level_roles = {}

        self.ready = False

        self.xp_per_msg = {str(const.guild_id): 1}

        self.anti_spam = {}

        self.async_tasks = {}

    async def check_levelup(self, msg: discord.Message):

        await self.client.wait_until_ready()

        if not self.ready:
            await asyncio.sleep(2)
            self.ready = True
        
        if msg.author.bot or msg.author.id == self.client.user.id:
            return

        if str(msg.author.id) not in self.client.lbs["msgs"].keys():
            self.client.lbs["msgs"][str(msg.author.id)] = 0
        self.client.lbs["msgs"][str(msg.author.id)] += 1

        anti_spam_ts = self.anti_spam.get(msg.author.id, None)
        if anti_spam_ts:
            if datetime.utcnow().timestamp() - anti_spam_ts < 7:
                return

        self.anti_spam[msg.author.id] = datetime.utcnow().timestamp()

        author_id = str(msg.author.id)

        await self.client.check_user(msg)

        try:
            guild_id = str(msg.guild.id)
        except AttributeError:
            return

        if guild_id not in self.client.lvlsys_config.keys():
            self.client.lvlsys_config[guild_id] = {"xp_required": 1000, "max_lvl": 100, "disabled_channels": []}
        
        if "disabled_channels" not in self.client.lvlsys_config[guild_id].keys():
            self.client.lvlsys_config[guild_id]["disabled_channels"] = []

        if msg.channel.id in self.client.lvlsys_config[guild_id]["disabled_channels"]:
            return

        xp_threshold = self.client.lvlsys_config[guild_id].get("xp_required", 1000)
        max_lvl = self.client.lvlsys_config[guild_id].get("max_lvl", 100)

        xp_per_msg = self.xp_per_msg.get(guild_id, 1)

        self.client.lbs["chatlb"][author_id]["total_xp"] += xp_per_msg
        avatar_url = str(msg.author.avatar_url_as(static_format="png", size=4096))
        if not isinstance(avatar_url, str):
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
        self.client.lbs["chatlb"][author_id]["url"] = avatar_url

        if self.client.lbs["chatlb"][author_id]["xp"] >= xp_threshold:
            
            self.client.lbs["chatlb"][author_id]["xp"] = 0
            
            before_level = self.client.lbs["chatlb"][author_id]["level"]
            self.client.lbs["chatlb"][author_id]["level"] = int(
                self.client.lbs["chatlb"][author_id]["total_xp"] // xp_threshold)

            if self.client.lbs["chatlb"][author_id]["level"] > max_lvl:
                self.client.lbs["chatlb"][author_id]["level"] = max_lvl
            
            if before_level < self.client.lbs["chatlb"][author_id]["level"]:
                if guild_id in self.level_roles.keys():
                    
                    for role in self.level_roles[guild_id].values():
                        await msg.author.remove_roles(role)

                    level = str(self.client.lbs["chatlb"][author_id]["level"])

                    if level in self.level_roles[guild_id].keys():
                        await msg.author.add_roles(self.level_roles[guild_id][level])

                em = discord.Embed(color=self.client.failure, title="You leveled up!",
                description=f"**Congratulations {msg.author.mention}, you are now level `{self.client.lbs['chatlb'][author_id]['level']}`!**")
                em.set_footer(icon_url=self.client.png, text="TitanMC | Level System")
                try:
                    await msg.reply(embed=em, delete_after=5)
                except (discord.NotFound, TypeError, AttributeError, discord.HTTPException):
                    # assuming discord is weird we ignore error (probably message arg not received properly)
                    pass
                return
        else:
            self.client.lbs["chatlb"][author_id]["xp"] += xp_per_msg

    @tasks.loop(count=1)
    async def load_level_roles(self):
        for guild in self.client.guilds:
            if (str(guild.id) in self.client.lvlsys_config) and (self.client.config[str(guild.id)].get("level_roles", False)):
                for level, role_id in self.client.config[str(guild.id)]["level_roles"].items():
                    role_obj = guild.get_role(role_id)
                    if role_obj:
                        self.level_roles[str(guild.id)][level] = guild.get_role 
                        
    
    @load_level_roles.before_loop
    async def before_load_level_roles(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, msg):
        await self.check_levelup(msg)

    
    @cog_slash(name="set_xp_threshold", description="[STAFF] Set the xp required to reach the next level", 
    guild_ids=const.slash_guild_ids, options=[
        create_option(name="new_xp", description="The xp required to reach next level", option_type=4, required=True)
    ])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def set_xp_threshold(self, ctx: SlashContext, new_xp:int=None):
        
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.defer(hidden=True)
            await ctx.send(f"**{self.client.no} | Failed!**", hidden=True)
            raise commands.MissingPermissions("Manage Roles")

        if str(ctx.guild_id) in self.client.lvlsys_config.keys():
            self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"] = new_xp
        
        else:
            self.client.lvlsys_config[str(ctx.guild_id)] = {"xp_required": new_xp, "max_lvl": 100, "level_roles": {}}

        for _id in self.client.lbs["chatlb"].keys():
            self.client.lbs["chatlb"][_id]["level"] = self.client.lbs["chatlb"][_id]["total_xp"] // new_xp
            if self.client.lbs["chatlb"][_id]["level"] > self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"]:
                self.client.lbs["chatlb"][_id]["level"] = self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"]

        with open("data/level_system/config.json", "w") as f:
                json.dump(self.client.lvlsys_config, f, indent=2)

        return await ctx.send(f"Users will now need to accumulate {new_xp} xp before they can level up!", hidden=True)


    @cog_slash(name="set_level_threshold", description="[STAFF] Set the max level somoene can reach", 
    guild_ids=const.slash_guild_ids, options=[
        create_option(name="new_level_cap", description="The max level someone can reach", option_type=4, required=True)
    ])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def set_level_threshold(self, ctx: SlashContext, new_level_cap:int=None):

        if not ctx.author.guild_permissions.manage_roles:
            await ctx.defer(hidden=True)
            await ctx.send(f"{self.client.no} | Failed!", hidden=True)
            raise commands.MissingPermissions("Manage Roles")

        if str(ctx.guild.id) in self.client.lvlsys_config.keys():
            self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"] = new_level_cap
        else:
            self.client.lvlsys_config[str(ctx.guild_id)] = {"xp_required": 1000, "max_lvl": new_level_cap, "level_roles": {}}

        for _id in self.client.lbs["chatlb"].keys():
            
            xp_req = self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"]
            self.client.lbs["chatlb"][_id]["level"] = self.client.lbs["chatlb"][_id]["total_xp"] // xp_req
            
            if self.client.lbs["chatlb"][_id]["level"] > new_level_cap:
                self.client.lbs["chatlb"][_id]["level"] = self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"]

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.client.lvlsys_config, f, indent=2) 

        return await ctx.send(f"The level cap has been set to `{new_level_cap}`", hidden=True)


    @cog_slash(name="set_level_role", description="[STAFF] Set the role for a specific leve",
    guild_ids=const.slash_guild_ids, 
    options=[
        create_option(name="level", description="The level you want to give a role to", option_type=4,
        required=True),
        create_option(name="role", description="The role that will be given when the user reaches that level", option_type=8, required=False)
        ])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_level_role(self, ctx:SlashContext, level:int=None, role:discord.Role=None):
                
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.defer(hidden=True)
            await ctx.send(f"{self.client.no} | Failed!", hidden=True)
            raise commands.MissingPermissions("Manage Roles")

        if role:
            if role.is_bot_managed():
                return await ctx.send("I cannot use that role as it is managed by a robot.", hidden=True)
            
            elif role.is_integration():
                return await ctx.send("I cannot use that role as it is managed by an integration.", hidden=True)

            elif role.is_default():
                return await ctx.send("I cannot use that role as it is a 'default' role", hidden=True)

            elif ctx.guild.roles.index(role) >= ctx.guild.roles.index(ctx.guild.me.top_role):
                return await ctx.send("Unfortunatelly I do not have enough permissiosn to manage that role.", hidden=True)

        if str(ctx.guild_id) not in self.client.lvlsys_config.keys():
            copy_dict = {"max_lvl": 100, "xp_required": 1000, "level_roles": {}}
        else:
            copy_dict = self.client.lvlsys_config[str(ctx.guild_id)].copy()

        if level > copy_dict["max_lvl"]:
            return await ctx.send(f"You cannot select a level higher than the max level (`{copy_dict['max_lvl']}`)", hidden=True)
        elif level < 0:
            return await ctx.send(f"You cannot select a level lower than 0.", hidden=True)

        if "level_roles" in copy_dict.keys():
            if role:
                copy_dict["level_roles"][str(level)] = role.id
            else:
                if str(level) not in copy_dict["level_roles"].keys():
                    return await ctx.send("There is no role configured for that level.", hidden=True)
                
                del copy_dict["level_roles"][str(level)]
        else:
            if role:
                copy_dict["level_roles"] = {str(level): role.id}
            else:
                return await ctx.send("You do not have any roles configuerd for any levels yet.", hidden=True)

        self.client.lvlsys_config[str(ctx.guild_id)] = copy_dict

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.client.lvlsys_config, f, indent=2)

        if role:
            return await ctx.send(f"Role {role.mention} will be given when a user reaches level `{level}`", hidden=True)
        else:
            return await ctx.send(f"When a user reaches level {str(level)}, they will no longer receive a role.", hidden=True)

    @cog_slash(name="display_level_roles", description="Display configured level roles", guild_ids=const.slash_guild_ids)
    async def display_level_roles(self, ctx:SlashContext):
        await ctx.defer(hidden=True)

        if (str(ctx.guild_id) not in self.client.lvlsys_config.keys()) or ("level_roles" not in self.client.lvlsys_config[str(ctx.guild_id)].keys()) or (
            not self.client.lvlsys_config[str(ctx.guild_id)]["level_roles"]
        ):
            return await ctx.send("There are no level roles set up for this guild yet!", hidden=True)



        em = discord.Embed(color=self.client.success, title="Level Roles")

        text = "\n".join([f"**{x[0]}** - <@&{x[1]}>" for x in self.client.lvlsys_config[str(ctx.guild_id)]["level_roles"].items()])
        
        em.description = text

        await ctx.embed(em)

    @cog_slash(name="level", description="Display your current level, ranking and xp till next level", guild_ids=const.slash_guild_ids,
    options=[create_option(name="member", description="The member to check the stats for.", option_type=6, required=False)])
    async def _level(self, ctx:SlashContext, member:discord.User=None):
        
        await ctx.defer(hidden=True)

        if not member:
            member = ctx.author

        elif not isinstance(member, int):
            member = member.id
        
        member_id = member.id if not isinstance(member, int) else member

        ranked = sorted(self.client.lbs["chatlb"], key=lambda f: self.client.lbs["chatlb"][f]["total_xp"], reverse=True)

        position = ranked.index(str(member_id)) + 1 if str(member_id) in ranked else "N/A"

        xp_next_lvl = f'{self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"] - self.client.lbs["chatlb"][str(member_id)]["xp"]}' if str(member_id) in self.client.lbs["chatlb"].keys() else "N/A"

        curr_xp =  f'{self.client.lbs["chatlb"][str(member_id)]["xp"]}/{self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"]}' if str(member_id) in self.client.lbs["chatlb"].keys() else "N/A"

        total_xp =  await self.client.round_int(self.client.lbs["chatlb"][str(member_id)]["total_xp"]) if str(member_id) in self.client.lbs["chatlb"].keys() else "N/A"

        curr_lvl = f'{self.client.lbs["chatlb"][str(ctx.author_id)]["level"]}' if str(member_id) in self.client.lbs["chatlb"].keys() else "N/A"

        em = discord.Embed(color=self.client.failure, title=self.client.lbs["chatlb"][str(member_id)]["name"] + "#" + self.client.lbs["chatlb"][str(member_id)]["disc"] if str(member_id) in self.client.lbs["chatlb"].keys() else f"{member_id}\nNot Ranked!")

        em.set_thumbnail(url=self.client.lbs["chatlb"][str(member_id)].get("url", None) if str(member_id) in self.client.lbs["chatlb"].keys() else member.avatar_url_as(static_format="png", size=4096) if not isinstance(member, int) else self.client.png)

        em.description = (
            "" + ("━"*14).center(30) + "\n"
            f"🏆 Level: **{curr_lvl}**" + "\n"
            f"👤 Leaderboard Ranking: **#{position}**".center(30) + "\n" 
            f"🎉 Current xp: **{curr_xp}**".center(30) + "\n"
            f"🥳 Total xp: **{total_xp}**".center(30) + "\n"
            f"⏳ XP until next level: **{xp_next_lvl}**".center(30) + "\n"
            "" + ("━"*14).center(30) + "\n"
            "Use **`/lb`** to see the leaderboard"
            )
        
        await ctx.embed(embed=em, footer="Level System")
    

    @cog_slash(name="add_xp", description="[STAFF] Add 'x' amount of xp to someone", guild_ids=const.slash_guild_ids, options=[
        create_option(name="user", description="The person to add xp to", option_type=6, required=True),
        create_option(name="amount", description="The amount of xp to add", option_type=4, required=True)
    ])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def add_xp(self, ctx:SlashContext, user:discord.User=None, amount:int=None):

        await ctx.defer(hidden=True)

        if amount <= 0:
            return await ctx.send("Failed. Amount must be >= 0", hidden=True)

        if str(user.id) not in self.client.lbs["chatlb"].keys():
            level = amount // self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"]

            if not isinstance(user, int):
                avatar_url = str(user.avatar_url_as(static_format="png", size=4096)) 
                if not isinstance(avatar_url, str):
                    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
            else:
                avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

            self.client.lbs["chatlb"][str(user.id)] = {
                    "name": str(user.name).encode('utf-8'),
                    "display_name": "N/A",
                    "disc": str(user.discriminator).encode('utf-8'),
                    "xp": 0,
                    "total_xp": amount,
                    "level":  level if level <= self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"] else self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"],
                    "url": avatar_url
                    }

        else:
            level = (amount  // self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"]) + self.client.lbs["chatlb"][str(user.id)]["level"]

            self.client.lbs["chatlb"][str(user.id)]["total_xp"] += amount
            self.client.lbs["chatlb"][str(user.id)]["level"] = level if level <= self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"] else self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"]

        return await ctx.send(f"Success! {user.mention}'s xp was increased by {amount}.", hidden=True)


    @cog_slash(name="remove_xp", description="[STAFF] Remove 'x' amount of xp from someone", guild_ids=const.slash_guild_ids, options=[
        create_option(name="user", description="The person to remove xp form", option_type=6, required=True),
        create_option(name="amount", description="The amount of xp to remove", option_type=4, required=True)
    ])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def remove_xp(self, ctx:SlashContext, user:discord.User=None, amount:int=None):

        await ctx.defer(hidden=True)

        if amount <= 0:
            return await ctx.send("Failed. Amount must be >= 0", hidden=True)

        if str(user.id) not in self.client.lbs["chatlb"].keys():
            return await ctx.send("That person isn't on the leaderboard therefore you cannot remove any xp from them.", hidden=True)


        level = ((self.client.lbs["chatlb"][str(user.id)]["total_xp"] - amount)  // self.client.lvlsys_config[str(ctx.guild_id)]["xp_required"])

        if level >= 0:
            self.client.lbs["chatlb"][str(user.id)]["total_xp"] -= amount
        else:
            self.client.lbs["chatlb"][str(user.id)]["total_xp"] = 0
            self.client.lbs["chatlb"][str(user.id)]["xp"] = 0

        self.client.lbs["chatlb"][str(user.id)]["level"] = level if level >= 0 and level <= self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"] else 0 if level <= 0 else self.client.lvlsys_config[str(ctx.guild_id)]["max_lvl"]

        return await ctx.send(f"Success! {user.mention}'s xp was decreased by {amount}.", hidden=True)


    @cog_slash(name="disable_xp", description="[STAFF] Disable XP gain in a specific channel", guild_ids=const.slash_guild_ids,
    options=[create_option(name="channel", description="The channel to disable XP gain in", option_type=7, required=True)])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def disable_xp(self, ctx:SlashContext, channel:discord.TextChannel=None):
        
        await ctx.defer(hidden=True)
        
        if "disabled_channels" not in self.client.lvlsys_config[str(ctx.guild_id)].keys():
            self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"] = []

        elif channel.id in self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"]:
            await ctx.channel.send("XP gain in that channel has already been disabled.", hidden=True)
            
            with open("data/level_system/config.json", "w") as f:
                json.dump(self.client.lvlsys_config, f, indent=2)
            
            return 

        self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"].append(channel.id)

        self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"] = list(set(self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"]))

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.client.lvlsys_config, f, indent=2)
        
        return await ctx.send(f"Disabled XP gain in <#{channel.id}>", hidden=True)

    
    @cog_slash(name="enable_xp", description="[STAFF] Enable XP gain in a disabled channel", guild_ids=const.slash_guild_ids,
    options=[create_option(name="channel", description="The channel to enable XP gain in", option_type=7, required=True)])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def enable_xp(self, ctx:SlashContext, channel:discord.TextChannel=None):
        
        await ctx.defer(hidden=True)

        if "disabled_channels" not in self.client.lvlsys_config[str(ctx.guild_id)].keys():
            return await ctx.channel.send("XP gain in that channel is enabled by default.", hidden=True)
        
        if channel.id not in self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"]:
            return await ctx.send("The XP gain in that channel is not disabled.", hidden=True)

        self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"].remove(channel.id)

        self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"] = list(set(self.client.lvlsys_config[str(ctx.guild_id)]["disabled_channels"]))

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.client.lvlsys_config, f, indent=2)
        
        return await ctx.send(f"Enabled XP gain in <#{channel.id}>", hidden=True)

    @cog_slash(name="xp_event", description="[STAFF] Create an event that will give x amount of xp per message for y duration", guild_ids=const.slash_guild_ids, options=[
        create_option(name="xp_per_message", description="The xp awarded per message during the event period", option_type=4, required=True), 
        create_option(name="duration", description="How long the event will last", option_type=3, required=True),
        create_option(name="optional_ping", description="A role to ping when event notifcation is sent (OPTIONAL)", option_type=8,
        required=False)])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def xp_event(self, ctx:SlashContext, xp_per_message:int=None, duration:str=None, optional_ping:discord.Role=None):
        
        await ctx.defer(hidden=True)
        
        duration = await self.client.format_duration(duration)

        if duration <= 0:
            return await ctx.send("Duration incorrect. Use format `5m`, `1w`, `1mo` to specify a duration.", hidden=True)
            
        if xp_per_message <= 0:
            return await ctx.send("XP per message must be 1 or higher.", hidden=True)
        
        ping = ""
        if optional_ping:
            ping = f"|| {optional_ping.mention} ||"

        if "event" not in self.client.lvlsys_config[str(ctx.guild_id)].keys():
            self.client.lvlsys_config[str(ctx.guild_id)]["event"] = {
                "timestamp": datetime.utcnow().timestamp() + duration + 5,
                "xp_per_message": xp_per_message}
            response = f"Event will begin shortly with {xp_per_message} xp per message and will end <t:{int(datetime.utcnow().timestamp() + duration)}:R>"

        elif self.client.lvlsys_config[str(ctx.guild_id)]["event"]["timestamp"] and datetime.utcnow().timestamp() < self.client.lvlsys_config[str(ctx.guild_id)]["event"]["timestamp"]:
            await ctx.send(f"Sorry, an event was already in progress. Try again when the event ends: <t:{int(self.client.lvlsys_config[str(ctx.guild_id)]['event']['timestamp'])}:R>", hidden=True)
            return

        else:
            self.client.lvlsys_config[str(ctx.guild_id)]["event"]["timestamp"] = datetime.utcnow().timestamp() + duration + 5
            self.client.lvlsys_config[str(ctx.guild_id)]["event"]["xp_per_message"] = xp_per_message
            response = f"Event is now will begin shortly with {xp_per_message} xp per message and will end <t:{int(datetime.utcnow().timestamp() + duration)}:R>"

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.client.lvlsys_config, f, indent=2)

        await ctx.send(response, hidden=True)

        await asyncio.sleep(5)
        
        await ctx.channel.send(f"🎉 **A XP event is starting. From now until** <t:{int(datetime.utcnow().timestamp() + duration)}> **you will receive {xp_per_message} xp per message!** 🥳 " + ping, allowed_mentions=discord.AllowedMentions(roles=True))
        
        self.xp_per_msg[str(ctx.guild.id)] = self.client.lvlsys_config[str(ctx.guild.id)]["event"]["xp_per_message"]

        self.async_tasks[str(ctx.guild_id)] = (self.client.loop.create_task(self.trigger_xp_event(ctx.guild_id, ctx.channel)), ctx.channel)
        # await self.trigger_xp_event(ctx.guild_id, ctx.channel)

        return

    @cog_slash(name="cancel_xp_event", description="[STAFF] Cancel an ongoing xp event", guild_ids=const.slash_guild_ids)
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def cancel_xp_event(self, ctx:SlashContext):
        await ctx.defer(hidden=True)
        task, channel = self.async_tasks.get(str(ctx.guild_id), None)
        if not task:
            return await ctx.send("There is no xp event in progress at the moment.", hidden=True)
        
        task.cancel()
        self.async_tasks.pop(str(ctx.guild_id), None)
        message = "⚠️ **XP event has been cancelled. Congratulations to those who participated!** ⚠️"
        await channel.send(message)

        self.client.lvlsys_config[str(ctx.guild_id)]["event"]["timestamp"] = None
        self.client.lvlsys_config[str(ctx.guild_id)]["event"]["xp_per_message"] = 1
        
        self.xp_per_msg.pop(str(ctx.guild_id), None)

        with open("data/level_system/config.json", "w") as f:
                json.dump(self.client.lvlsys_config, f, indent=2)

        return await ctx.send("Event cancelled!", hidden=True)


    async def trigger_xp_event(self, request_guild_id:int=None, channel:discord.TextChannel=None):
        if "event" in self.client.lvlsys_config[str(request_guild_id)].keys():
            ts = self.client.lvlsys_config[str(request_guild_id)]["event"]["timestamp"]
            
            await discord.utils.sleep_until(datetime.fromtimestamp(ts))
            
            try:
                await channel.send("⚠️ **XP event has ended. Congratulations to those who participated!** ⚠️") if channel else None
            except discord.HTTPException:
                # Channel probably deleted, ignore error
                pass

            self.client.lvlsys_config[str(request_guild_id)]["event"]["timestamp"] = None
            self.client.lvlsys_config[str(request_guild_id)]["event"]["xp_per_message"] = 1
            
            self.xp_per_msg.pop(str(request_guild_id), None)

            self.async_tasks.pop(str(request_guild_id), None)
                    
            with open("data/level_system/config.json", "w") as f:
                json.dump(self.client.lvlsys_config, f, indent=2)


def setup(client):
    client.add_cog(LevelSystem(client=client))
