import asyncio
import discord
import json

from constants import const

from discord.ext import commands, tasks
from utils.dpy import Converters

from discord_slash import cog_ext, ComponentContext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_actionrow, create_button
from discord_slash.model import ButtonStyle


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

    @cog_ext.cog_slash(name="setup_verification_button", description="[STAFF] Add a verification button to a message", guild_ids=const.slash_guild_ids, options=[
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


    @cog_ext.cog_slash(name="set_verification_role", description="[STAFF] The role that will be given to users whenver they get verified", guild_ids=const.slash_guild_ids, options=[create_option(name="role", description="The verification role to be given", option_type=8, required=True)])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_verification_role(self, ctx:SlashContext, role:discord.Role=None):

        self.verification_role = role

        with open("data/verification.json", "w") as f:
            self.v_role_data[str(ctx.guild.id)] = role.id
            json.dump(self.v_role_data, f, indent=2)

        await ctx.send("Success!", hidden=True)
    

    @cog_ext.cog_slash(name="verify", description="[STAFF] Forcefully verify a memebr or all unverified members", guild_ids=const.slash_guild_ids, options=[   
        create_option(name="member", description="The member to verify forcefully", option_type=6, required=False),
        create_option(name="otherwise", description="Forcefully verify everyone that isn't verified", option_type=3, required=False, choices=[create_choice(value="otherwise", name="All unverified members")]) | {"focused": True}
        ])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def verify(self, ctx:SlashContext, member:discord.Member=None, otherwise:str=None):

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
