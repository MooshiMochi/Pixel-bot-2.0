import asyncio
import discord
import json

from discord.ext import commands, tasks

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from constants import const


class LevelSystem(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.level_roles = {}

        self.ready = False

        with open("data/level_system/config.json", "r") as f:
            self.config = json.load(f)

        with open("data/level_system/chatlb.json", "r") as f:
            self.client.chatlb = json.load(f)

    async def check_levelup(self, msg: discord.Message):

        await self.client.wait_until_ready()

        if not self.ready:
            await asyncio.sleep(2)
            self.ready = True

        if msg.author.id == self.client.user.id:
            return

        author_id = str(msg.author.id)

        await self.client.check_user(msg)

        if str(msg.guild.id) not in self.config.keys():
            self.config[str(msg.guild.id)] = {"xp_required": 1000, "max_lvl": 100}

        xp_threshold = self.config[str(msg.guild.id)].get("xp_required", 1000)
        max_lvl = self.config[str(msg.guild.id)].get("max_lvl", 100)

        self.client.chatlb[author_id]["total_xp"] += 1

        if self.client.chatlb[author_id]["xp"] >= xp_threshold:
            
            self.client.chatlb[author_id]["xp"] = 0

            if self.client.chatlb[author_id]["level"] < max_lvl:
                self.client.chatlb[author_id]["level"] += 1
                
                if str(msg.guild.id) in self.level_roles.keys():
                    
                    for role in self.level_roles[str(msg.guild.id)].values():
                        await msg.author.remove_roles(role)

                    level = str(self.client.chatlb[author_id]["level"])

                    if level in self.level_roles[str(msg.guild.id)].keys():
                        await msg.author.add_roles(self.level_roles[str(msg.guild.id)][level])

                em = discord.Embed(color=self.client.success, title="You leveld up!",
                description=f"**Congratulations, you are now level `{self.client.chatlb[author_id]['level']}`!")
                em.set_footer(icon_url=self.client.png, text="Pixel | Level System")

                await msg.reply(emebd=em)
                return
        
        self.client.chatlb[author_id]["xp"] += 1


    @tasks.loop(count=1)
    async def load_level_roles(self):
        for guild in self.client.guilds:
            if (str(guild.id) in self.config) and (self.client.config[str(guild.id)].get("level_roles", False)):
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

    
    @cog_slash(name="set_xp_threshold", description="Set the xp required to reach the next level", 
    guild_ids=[const.guild_id], options=[
        create_option(name="new_xp", description="The xp required to reach next level", option_type=4, required=True)
    ])
    async def set_xp_threshold(self, ctx: SlashContext, new_xp:int=None):
        
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.defer(hidden=True)
            await ctx.send(f"**{self.client.no} | Failed!**", hidden=True)
            raise commands.MissingPermissions("Manage Roles")

        if str(ctx.guild_id) in self.config.keys():
            self.config[str(ctx.guild_id)]["xp_required"] = new_xp
        
        else:
            self.config[str(ctx.guild_id)] = {"xp_required": new_xp, "max_lvl": 100, "level_roles": {}}

        with open("data/level_system/config.json", "w") as f:
                json.dump(self.config, f, indent=2)

        return await ctx.send(f"Users will now need to accumulate {new_xp} xp before they can level up!", hidden=True)


    @cog_slash(name="set_level_threshold", description="Set the max level somoene can reach", 
    guild_ids=[const.guild_id], options=[
        create_option(name="new_level_cap", description="The max level someone can reach", option_type=4, required=True)
    ])
    async def set_level_threshold(self, ctx: SlashContext, new_level_cap:int=None):

        if not ctx.author.guild_permissions.manage_roles:
            await ctx.defer(hidden=True)
            await ctx.send(f"{self.client.no} | Failed!", hidden=True)
            raise commands.MissingPermissions("Manage Roles")

        if str(ctx.guild.id) in self.config.keys():
            self.config[str(ctx.guild_id)]["max_lvl"] = new_level_cap
        else:
            self.config[str(ctx.guild_id)] = {"xp_required": 1000, "max_lvl": new_level_cap, "level_roles": {}}

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.config, f, indent=2) 

        return await ctx.send(f"The level cap has been set to `{new_level_cap}`", hidden=True)


    @cog_slash(name="set_level_role", description="Set the role for a specific leve",
    guild_ids=[const.guild_id], 
    options=[
        create_option(name="level", description="The level you want to give a role to", option_type=4,
        required=True),
        create_option(name="role", description="The role that will be given when the user reaches that level", option_type=8, required=False)
        ])
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

        if str(ctx.guild_id) not in self.config.keys():
            copy_dict = {"max_lvl": 100, "xp_required": 1000, "level_roles": {}}
        else:
            copy_dict = self.config[str(ctx.guild_id)].copy()

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

        self.config[str(ctx.guild_id)] = copy_dict

        with open("data/level_system/config.json", "w") as f:
            json.dump(self.config, f, indent=2)

        if role:
            return await ctx.send(f"Role {role.mention} will be given when a user reaches level `{level}`", hidden=True)
        else:
            return await ctx.send(f"When a user reaches level {str(level)}, they will no longer receive a role.", hidden=True)

    @cog_slash(name="display_level_roles", description="Display configured level roles", guild_ids=[const.guild_id])
    async def display_level_roles(self, ctx:SlashContext):

        await ctx.defer(hidden=True)
        
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.send(f"{self.client.no} | Failed!", hidden=True)
            raise commands.MissingPermissions("Manage Roles")


        if (str(ctx.guild_id) not in self.config.keys()) or ("level_roles" not in self.config[str(ctx.guild_id)].keys()) or (
            not self.config[str(ctx.guild_id)]["level_roles"]
        ):
            return await ctx.send("There are no level roles set up for this guild yet!", hidden=True)



        em = discord.Embed(color=self.client.success, title="Level Roles")

        text = "\n".join([f"**{x[0]}** - <@&{x[1]}>" for x in self.config[str(ctx.guild_id)]["level_roles"].items()])
        
        em.description = text

        await ctx.embed(em)

def setup(client):
    client.add_cog(LevelSystem(client=client))
