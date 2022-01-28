import discord
import json

from constants import const

from discord.ext import commands, tasks

from discord_slash import cog_ext, ComponentContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_actionrow, create_button
from discord_slash.model import ButtonStyle


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

    @cog_ext.cog_slash(name="set_verification_button", description="Add a verification button to a message", guild_ids=[const.guild_id], options=[
        create_option(name="verification_role", description="The role to give users when the button is pressed", option_type=8, required=True),
        create_option(name="send_as_embed", description="Choose whether to send the message as an embed or not.", option_type=3,
        required=True, choices=[
            create_choice(value="yes", name="Send as embed"),
            create_choice(value="no", name="Send as text")]),
        create_option(name="content", description="The contents of the verification message", option_type=3, required=True),
        create_option(name="title", description="The title of the message that will be sent", option_type=3, required=False)        
            ])
    async def verification_setup(self, ctx, verification_role:discord.Role=None, send_as_embed:str=None, title:str=None, content:str=None):
        
        await ctx.defer(hidden=True)

        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send("You do not have permissions to use this command", hidden=True)
        
        action_row = create_actionrow(*[create_button(style=ButtonStyle.green, label="Get Verified!", custom_id="verification_button")])
        
        await ctx.send("Success!", hidden=True)

        if send_as_embed:
            em = discord.Embed(color=self.client.success)
            em.set_footer(text="Pixel | Verification", icon_url=self.client.png)
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
            self.v_role_data = {str(ctx.guild.id): verification_role.id}
            json.dump(self.v_role_data, f, indent=2)

    
    @commands.Cog.listener()
    async def on_component(self, ctx: ComponentContext):
        if ctx.custom_id == "verification_button":
            await ctx.defer(hidden=True)

            if self.verification_role in ctx.author.roles:
                em = discord.Embed(color=self.client.failure, description="You are already verified!")
            else:
                em = discord.Embed(color=self.client.success, description="You are now verified!")
                await ctx.author.add_roles(self.verification_role)

            em.set_footer(text="Pixel | Verification", icon_url=self.client.png)

            return await ctx.send(embed=em, hidden=True)
            

def setup(client):
    client.add_cog(Verification(client))
