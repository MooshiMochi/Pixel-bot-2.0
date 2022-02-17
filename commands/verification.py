import asyncio
import discord
import json

from constants import const

from discord.ext import commands, tasks
from utils.dpy import Converters
from utils.exceptions import NotVerified, Verified

from discord_slash import ComponentContext, SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_actionrow, create_button
from discord_slash.model import ButtonStyle
from discord_slash.error import RequestFailure
from discord_slash.model import BucketType


bool_converter = Converters.Boolean


class Verification(commands.Cog):
    def __init__(self, client):
        self.client = client
        
        self.verification_role = 0

        with open("data/verification.json", "r") as f:
            self.v_role_data = json.load(f)
            if not str(const.guild_id) in self.v_role_data:
                self.v_role_data = {str(const.guild_id): 0}

            self.verification_role = self.v_role_data[str(const.guild_id)]

        self.get_verification_role.start()

    def cog_unload(self):
        self.get_verification_role.cancel()

    @tasks.loop(count=1)
    async def get_verification_role(self):
        if isinstance(self.verification_role, int):
            self.verification_role = self.client.get_guild(const.guild_id).get_role(self.verification_role)
        

    @get_verification_role.before_loop
    async def before_get_verification_role(self):
        await self.client.wait_until_ready()


    @cog_slash(name="setup_verification_button", description="[STAFF] Add a verification button to a message", guild_ids=const.slash_guild_ids, options=[
        create_option(name="verification_role", description="The role to give users when the button is pressed", option_type=8, required=True),
        create_option(name="send_as_embed", description="Choose whether to send the message as an embed or not.", option_type=3,
        required=True, choices=[
            create_choice(value="yes", name="Send as embed"),
            create_choice(value="no", name="Send as text")]),
        create_option(name="content", description="The contents of the verification message", option_type=3, required=True),
        create_option(name="title", description="The title of the message that will be sent", option_type=3, required=False)        
            ])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def setup_verification_button(self, ctx, verification_role:discord.Role=None, send_as_embed:str=None, title:str=None, content:str=None):
        
        await ctx.defer(hidden=True)

        if verification_role.is_bot_managed() or verification_role.is_integration() or verification_role.is_default():
            return await ctx.send("Invalid Verification Role! Use /set_verification_role to set a new verification role.", hidden=True)
        
        elif ctx.guild.roles.index(verification_role) >= ctx.guild.roles.index(ctx.guild.me.top_role):
            return await ctx.send(f"Unfortunatelly I do not have enough permissiosn to manage {verification_role.mention}. Please move it below my top role and try again!", hidden=True)
        
        action_row = create_actionrow(*[create_button(style=ButtonStyle.green, label="Get Verified!", custom_id="verification_button")])
        
        await ctx.send("Success!", hidden=True)

        send_as_embed = await bool_converter.convert(ctx, send_as_embed)

        if send_as_embed:
            em = discord.Embed(color=self.client.success)
            em.set_footer(text="TN | Verification", icon_url=self.client.png)
            em.description = content

            if title:
                em.title=title

            await ctx.channel.send(embed=em, components=[action_row])
        
        else:
            message = ""
            if title:
                message = f"**{title}**\n\n"
            
            message += content

            await ctx.channel.send(content=message, components=[action_row])
        
        self.verification_role = verification_role

        with open("data/verification.json", "w") as f:
            self.v_role_data[str(ctx.guild.id)] = verification_role.id
            json.dump(self.v_role_data, f, indent=2)


    @cog_slash(name="set_verification_role", description="[STAFF] The role that will be given to users whenver they get verified", guild_ids=const.slash_guild_ids, options=[create_option(name="role", description="The verification role to be given", option_type=8, required=True)])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_verification_role(self, ctx:SlashContext, role:discord.Role=None):

        self.verification_role = role

        with open("data/verification.json", "w") as f:
            self.v_role_data[str(ctx.guild.id)] = role.id
            json.dump(self.v_role_data, f, indent=2)

        await ctx.send("Success!", hidden=True)
    

    @cog_slash(name="force_verify", description="[STAFF] Forcefully verify a memebr or all unverified members", guild_ids=const.slash_guild_ids, options=[   
        create_option(name="member", description="The member to verify forcefully", option_type=6, required=False),
        create_option(name="otherwise", description="Forcefully verify everyone that isn't verified", option_type=3, required=False, choices=[create_choice(value="otherwise", name="All unverified members")]) | {"focused": True}
        ])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def force_verify(self, ctx:SlashContext, member:discord.Member=None, otherwise:str=None):

        await self.client.wait_until_ready()

        if not self.verification_role:
                return await ctx.embed(embed=(discord.Embed(color=self.client.failure, description="The verification role was not set up!")), footer="Verification")

        if self.verification_role.is_bot_managed() or self.verification_role.is_integration() or self.verification_role.is_default():
            return await ctx.send("Invalid Verification Role! Use /set_verification_role to set a new verification role.", hidden=True)
        
        elif ctx.guild.roles.index(self.verification_role) >= ctx.guild.roles.index(ctx.guild.me.top_role):
            return await ctx.send(f"Unfortunatelly I do not have enough permissiosn to manage {self.verification_role.mention}. Please move it below my top role!", hidden=True)

        if member and otherwise:
            if self.verification_role not in member.roles:
                await member.add_roles(self.verification_role)
                return await ctx.send(f"Forcefully verified {member.mention}!", hidden=True)
            return await ctx.send(f"{member.mention} is already verified!", hidden=True)
        
        elif member and not otherwise:
            if self.verification_role not in member.roles:
                await member.add_roles(self.verification_role)
                return await ctx.send(f"Forcefully verified {member.mention}!", hidden=True)
            return await ctx.send(f"{member.mention} is already verified!", hidden=True)
        
        elif not member and otherwise:

            unverified_members = [x for x in ctx.guild.members if self.verification_role not in x.roles and not x.bot]

            if not unverified_members:
                return await ctx.send("All members are already verified!", hidden=True)
            
            em = discord.Embed(color=self.client.success, description=f"Attempting to verify {len(unverified_members)} members. ETA {await self.client.sec_to_time((len(unverified_members)//10)*6 + 5)}")
            em.set_footer(text="TN | Verification", icon_url=self.client.png)

            await ctx.send(embed=em, hidden=True)

            success = 0
            fail = 0

            for member_tup in enumerate(unverified_members):
                
                try:
                    await member_tup[1].add_roles(self.verification_role)
                    success += 1
                except discord.HTTPException:
                    fail += 1

                if member_tup[0] % 10 == 0:
                    await asyncio.sleep(5)

            em = discord.Embed(color=self.client.success if fail < success else self.client.failure, 
            description=f"**Attempted to forcefully verify {len(unverified_members)} members.**\n\n{self.client.yes} **|** Successfull verifications: `{success}`\n{self.client.no} **|** Failed verifications: `{fail}`")
            em.set_footer(text="TN | Verification", icon_url=self.client.png)
            await ctx.send(embed=em, hidden=True)

    
    @cog_slash(name="link", description="Link your discord account with a minecraft account.", guild_ids=const.slash_guild_ids, options=[
        create_option(name="player_name", description="Your account's username in Minecraft", option_type=3, required=True)
    ])
    @commands.cooldown(1, 5, BucketType.member)
    async def link(self, ctx:SlashContext, player_name:str=None):
        await ctx.defer(hidden=True)

        if self.client.players.get(str(ctx.author_id), None):
            raise Verified

        async with self.client.session.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}") as res:
            if res.status != 200:
                raise RequestFailure(res.status, (await res.json())["errorMessage"])
            
            resp = await res.json()
        
        if resp["name"] in self.client.players.values() and self.client.players.get(str(ctx.author_id), None) != resp["name"]:
            return await ctx.send("It seems someone has already verified with that username. If you believe this is wrong, please contact one of the staff members.", hidden=True)
        
        self.client.players[str(ctx.author_id)] = resp["name"]
        
        em = discord.Embed(title="Verification Successfull!", description=f"Your account has been linked to `{resp['name']}`.")
        em.set_author(name=ctx.author, icon_url=ctx.author.avatar_url_as(static_format="png", size=4096))
        em.set_thumbnail(url=f"http://cravatar.eu/helmhead/{resp['name']}/256.png")
        em.set_footer(text="TN | Verification", icon_url=self.client.png)
        em.color = self.client.success

        try:
            return await ctx.send(embed=em, hidden=True)
        except (discord.HTTPException, discord.Forbidden):
            return

    @cog_slash(name="unlink", description="Unlick a minecraft account from your discord account", guild_ids=const.slash_guild_ids)
    async def unlink(self, ctx:SlashContext):
        await ctx.defer(hidden=True)

        user = self.client.players.get(str(ctx.author_id), None)
        if not user:
            raise NotVerified
        
        self.client.players.pop(str(ctx.author_id), None)

        em = discord.Embed(title="Unlinked Successfully!", description=f"Your account has been unlinked from `{user}`.")
        em.set_author(name=ctx.author, icon_url=ctx.author.avatar_url_as(static_format="png", size=4096))
        em.set_thumbnail(url=f"http://cravatar.eu/helmhead/{user}/256.png")
        em.set_footer(text="TN | Verification", icon_url=self.client.png)
        em.color = self.client.success
        try:
            return await ctx.send(embed=em)
        except (discord.HTTPException, discord.Forbidden):
            return

    @cog_slash(name="force_link", description="[STAFF] Forcefully link a minecraft username to someone's discord account", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The memebr to forcefully link to a minecraft account.", option_type=6, required=True),
        create_option(name="player_name", description="The minecraft username that they will be linked to", option_type=3, required=True)
    ])
    @commands.cooldown(1, 5, BucketType.guild)
    @commands.has_permissions(manage_nicknames=True)
    async def force_link(self, ctx:SlashContext, member:discord.Member=None, player_name:str=None):
        await ctx.defer(hidden=True)

        async with self.client.session.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}") as res:
            if res.status != 200:
                raise RequestFailure(res.status, (await res.json())["errorMessage"])
            
            resp = await res.json()
        
        cont = ""
        if resp["name"] in self.client.players.values() and self.client.players.get(str(member.id), None) != resp["name"]:
            cont = "It seems someone has already verified with that username. They were unlinked"
        
        for key, val in self.client.players.items():
            if val.lower() == player_name.lower():
                self.client.players.pop(key, None)
                break

        self.client.players[str(member.id)] = resp["name"]
        
        em = discord.Embed(title="Verification Successfull!", description=f"{member.mention} has been linked to `{resp['name']}`.")
        em.set_author(name=member, icon_url=member.avatar_url_as(static_format="png", size=4096))
        em.set_thumbnail(url=f"http://cravatar.eu/helmhead/{resp['name']}/256.png")
        em.set_footer(text="TN | Verification", icon_url=self.client.png)
        em.color = self.client.success

        opts = {"embed": em}
        if cont:
            opts["content"] = cont

        try:
            return await ctx.send(**opts, hidden=True)
        except (discord.HTTPException, discord.Forbidden):
            return


    @cog_slash(name="force_unlink", description="[STAFF] Forcefully unlink a minecraft username from someone's discord account", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The memebr to forcefully unlink", option_type=6, required=True)
    ])
    @commands.has_permissions(manage_nicknames=True)
    async def force_unlink(self, ctx:SlashContext, member:discord.Member=None, player_name:str=None):
        await ctx.defer(hidden=True)

        user = self.client.players.get(str(member.id), None)
        if not user:
            raise NotVerified
        
        self.client.players.pop(str(member.id), None)

        em = discord.Embed(title="Unlinked Successfully!", description=f"{member.mention} account has been unlinked from `{user}`.")
        em.set_author(name=member, icon_url=member.avatar_url_as(static_format="png", size=4096))
        em.set_thumbnail(url=f"http://cravatar.eu/helmhead/{user}/256.png")
        em.set_footer(text="TN | Verification", icon_url=self.client.png)
        em.color = self.client.success
        try:
            return await ctx.send(embed=em)
        except (discord.HTTPException, discord.Forbidden):
            return

    
    @commands.Cog.listener()
    async def on_component(self, ctx: ComponentContext):
        if ctx.custom_id == "verification_button":
            await ctx.defer(hidden=True)

            if not self.verification_role:
                return await ctx.embed(embed=(discord.Embed(color=self.client.failure, description="The verification role was not set up!")), footer="Verification")

            if self.verification_role in ctx.author.roles:
                em = discord.Embed(color=self.client.failure, description="You are already verified!")
            else:
                em = discord.Embed(color=self.client.success, description="You are now verified!")
                await ctx.author.add_roles(self.verification_role)

            em.set_footer(text="TN | Verification", icon_url=self.client.png)

            return await ctx.send(embed=em, hidden=True)

def setup(client):
    client.add_cog(Verification(client))
