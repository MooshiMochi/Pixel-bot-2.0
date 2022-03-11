import asyncio

from discord.ext import commands

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash, cog_context_menu

from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow

from discord_slash.context import MenuContext
from discord_slash.model import ContextMenuType

from constants import const

class Experimental(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

    @cog_slash(name="create_select", description="[DEVELOPER] Create select", guild_ids=const.slash_guild_ids)
    @commands.is_owner()
    async def create_select(self, ctx:SlashContext):
        await ctx.defer(hidden=False)

        select = create_select(options=[

            create_select_option(label="Opt 1", value="select_1", emoji="🥳", description="First select", default=True),
            create_select_option(label="Opt 2 💸", value="select_2", emoji="🎉")
        ],
        placeholder="Yeet", min_values=1, max_values=1, disabled=False, custom_id="Restricted")

        await ctx.send("test", components=[create_actionrow(select)], hidden=False)
        # print(create_actionrow(select))
    
    @cog_context_menu(name="Add reaction role", guild_ids=const.slash_guild_ids, target=ContextMenuType.MESSAGE)
    async def add_reaction_role(self, ctx: MenuContext):
        await ctx.defer(hidden=True)

        await ctx.send("Please provide the emoji, role and description of the reaction role you want to add in the format `@role | emoji | description`", hidden=ctx._deferred_hidden)

        while 1:
            try:
                msg = await self.client.wait_for("message", check=lambda msg: msg.author.id == ctx.author_id, timeout=60)
                content = msg.content.replace(" | ", "|")
                li = content.split("|")
                li[0] = li[0].replace("<@&", "").replace(">", "")
                try:
                    li[0] = int(li[0])
                except ValueError:
                    await ctx.send("The role was invalid. Please ping a role!", hidden=ctx._deferred_hidden)

                ctx.target_message.components[0]["components"][0]["options"].append(
                    create_select_option(label=f"<@&{li[0]}>", value=li[0], emoji=li[1], description=li[2])
                )
                await ctx.target_message.edit(ctx.target_message.content, components=ctx.target_message.components[0])
                
                await ctx.send(msg.content, hidden=ctx._deferred_hidden)
            except asyncio.TimeoutError:
                await ctx.send("Cancelled!", hidden=ctx._deferred_hidden)
                break
        # else:  
        #     await ctx.send(f"Target Components: {ctx.target_message.components}", hidden=ctx._deferred_hidden)


    @commands.Cog.listener()
    async def on_component(self, ctx:ComponentContext):
        await self.client.wait_until_ready()
        
        if ctx.custom_id != "Restricted":
            return

        print(ctx.component)

        await ctx.send(f"You selected {ctx.selected_options}")


def setup(client):
    client.add_cog(Experimental(client))