import json
import discord

from discord.ext import commands, tasks

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option 

from utils.exceptions import InvalidURLError

from datetime import datetime

from utils.dpy import url

from constants import const

class Suggestions(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.fill_str = "\u200b \u200b \u200b \u200b \u200b \u200b \u200b "

        with open("data/suggestions_config.json", "r") as f:
            self.config = json.load(f)
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}][Suggestions]> Loaded suggestions config.\n")

            if not "enabled" in self.config.keys():
                self.config["enabled"] = False

            if not "suggestion_channel_id" in self.config.keys():
                self.config["suggestion_channel_id"] = None
            
            if not "max_upvotes" in self.config.keys():
                self.config["max_upvotes"] = 15
            
            if not "staff_vote_channel_id" in self.config.keys():
                self.config["staff_vote_channel_id"] = None
        
        self.suggestions_channel = self.config["suggestion_channel_id"]
        self.staff_vote_channel = self.config["staff_vote_channel_id"]
        
        self.get_ready.start()

    @tasks.loop(count=1)
    async def get_ready(self):
        # guild = self.client.get_guild(const.guild_id)
        self.suggestions_channel = self.client.get_channel(self.suggestions_channel) if self.suggestions_channel else None
        self.staff_vote_channel = self.client.get_channel(self.staff_vote_channel) if self.staff_vote_channel else None

    @get_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()
    
    @cog_slash(name="suggest", description="Make a suggestion to our staff team", guild_ids=const.slash_guild_ids,
    options=[
        create_option(name="title", description="The title to generalise what your suggestion is about", option_type=3, required=True),
        create_option(name="content", description="The suggestion itself", option_type=3, required=True),
        create_option(name="other_details", description="Any other details you would like to specify", option_type=3, required=False),
        create_option(name="optional_image", description="An images you would like to provide (URL ONLY)", option_type=3, required=False)
    ])
    async def suggest(self, ctx:SlashContext, title:str=None, content:str=None, other_details:str=None, optional_image:str=None):
        await ctx.defer(hidden=True)

        if not self.config["enabled"]:
            return await ctx.send("This server does not have suggestions enabled.", hidden=True)

        description = content

        em = discord.Embed(title=title)
        em.set_author(name=f"A new suggestion by {ctx.author}")
        
        if other_details:
            description += f"\n\n**__Other Details__**\n{other_details}\n\u200b"
        else:
            description += "\n\u200b"

        if optional_image:
            try:
                em.set_image(url=url(optional_image))
            except InvalidURLError as e:
                _em = discord.Embed(description=f"**The url: '{str(optional_image)}' is not valid!**", color=self.client.failure)
                _em.set_footer(text="TitanMC | Suggestions")
                return await ctx.send(embed=_em, hidden=True)

        em.description = description

        em.set_footer(text=f"TitanMC | Suggestions | {datetime.utcnow().date()}", icon_url=self.client.png)

        em.set_thumbnail(url=ctx.author.avatar_url_as(static_format="png", size=2048))
        
        em.add_field(name="▶️ Status:", 
                    value=self.fill_str + "💬 This suggestion is still waiting for an official answer!")


        msg = await self.suggestions_channel.send(embed=em)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        return await ctx.send("Suggestion has been sent!", hidden=True)

    
    @cog_slash(name="accept_suggestion", description="[STAFF] Mark a suggestion as 'Accepted'", guild_ids=const.slash_guild_ids, options=[
        create_option(name="message_id", description="The message ID of the suggestion", option_type=3, required=True),
        create_option(name="response_message", description="The response that will appear in the suggestion", option_type=3, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def accept_suggestion(self, ctx:SlashContext, message_id:str=None, response_message:str=None):
        await ctx.defer(hidden=True)

        try:
            message_id = int(message_id)
        except ValueError:
            return await ctx.send("Invalid message ID provided! (It must be a number)", hidden=True)

        msg = await self.suggestions_channel.fetch_message(message_id)
        if not msg:
            return await ctx.send("Could not find that suggestion. Please check and try again!", hidden=True)
        
        if len(msg.embeds) <= 0:
            return await ctx.send("That is not a valid suggestion.", hidden=True)
        
        em = msg.embeds[0]

        if (str(em.color) == "#00ff00") or (str(em.color) == "#ff0000"):
            return await ctx.send("That suggestion has already been responded to!", hidden=True)

        em.color = self.client.success
        if response_message:
            em.add_field(name=f"🛂 Staff Answer: ({ctx.author}):",
                        value=self.fill_str + response_message)

        em.set_field_at(0, name="▶️ Status:", 
                value=self.fill_str + "✅ This suggestion has been accepted!")
        
        await msg.edit(embed=em)
        return await ctx.send("Suggestion Accepted!", hidden=True)

    
    @cog_slash(name="deny_suggestion", description="[STAFF] Mark a suggestion as 'Denied'", guild_ids=const.slash_guild_ids, options=[
        create_option(name="message_id", description="The message ID of the suggestion", option_type=3, required=True),
        create_option(name="response_message", description="The response that will appear in the suggestion", option_type=3, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def deny_suggestion(self, ctx:SlashContext, message_id:str=None, response_message:str=None):
        await ctx.defer(hidden=True)

        try:
            message_id = int(message_id)
        except ValueError:
            return await ctx.send("Invalid message ID provided! (It must be a number)", hidden=True)

        msg = await self.suggestions_channel.fetch_message(message_id)
        if not msg:
            return await ctx.send("Could not find that suggestion. Please check and try again!", hidden=True)
        
        if len(msg.embeds) <= 0:
            return await ctx.send("That is not a valid suggestion.", hidden=True)
        
        em = msg.embeds[0]
        
        if (str(em.color) == "#00ff00") or (str(em.color) == "#ff0000"):
            return await ctx.send("That suggestion has already been responded to!", hidden=True)

        em.color = self.client.failure
        if response_message:
            em.add_field(name=f"🛂 Staff Answer: ({ctx.author}):",
                        value=self.fill_str + response_message)

        em.set_field_at(0, name="▶️ Status:", 
                value=self.fill_str + "❌ This suggestion has been denied!")
        
        await msg.edit(embed=em)
        return await ctx.send("Suggestion Denied!", hidden=True)


    @cog_slash(name="config_suggestions", description="[ADMIN] Configure suggestions for this guild", guild_ids=const.slash_guild_ids, options=[
        create_option(name="enabled", description="Just as the name suggests", required=True, option_type=5),
        create_option(name="suggestions_channel", description="The channel where user suggestions will be sent to", option_type=7, required=False),
        create_option(name="staff_vote_channel", description="The channel where the suggestions will be sent after x upvotes", option_type=7, required=False),
        create_option(name="max_upvotes", description="Upvotes required until suggesiton is sent to staff votes", option_type=4, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def config_suggestions(self, ctx:SlashContext, enabled:bool=False, suggestions_channel:discord.TextChannel=None, staff_vote_channel:discord.TextChannel=None, max_upvotes:int=None):
        await ctx.defer(hidden=True)

        em = discord.Embed(color=self.client.failure, title="Suggestions Config Finished", description="")

        before_enabled = self.config["enabled"]
        before_suggestions_channel = self.config["suggestion_channel_id"]
        before_staff_vote_channel = self.config["staff_vote_channel_id"]
        before_max_upvotes = self.config["max_upvotes"]

        if enabled:
            if not suggestions_channel:
                return await ctx.send("Param 'suggestions_channel' must be provided if 'enabled' is set to True!", hidden=True)
            
            if not all((staff_vote_channel, max_upvotes)):
                return await ctx.send("Param `staff_vote_channel` and `max_upvotes` must BOTH be specified if `staff_vote_channel` or `max_upvotes` param is set to True", hidden=True)
            
            if before_enabled != enabled:
                em.description += f"Enabled: `{enabled}`\n"
            else:
                em.description += f"Enabled: `{enabled}` (unchanged)\n"

            if before_suggestions_channel != suggestions_channel.id:
                em.description += f"Suggestion Channel: <#{suggestions_channel.id}>\n"
            else:
                em.description += f"Suggestion Channel: <#{suggestions_channel.id}> (unchanged)\n"
            
            self.config["enabled"] = enabled
            self.config["suggestion_channel_id"] = suggestions_channel.id
            self.suggestions_channel = suggestions_channel

            if staff_vote_channel:
                if before_staff_vote_channel != staff_vote_channel.id:
                    em.description += f"Staff Vote Channel: <#{staff_vote_channel.id}>\n"
                else:
                    em.description += f"Staff Vote Channel: <#{staff_vote_channel.id}> (unchanged)\n"
                
                if before_max_upvotes != max_upvotes:
                    em.description += f"Max Upvotes: `{max_upvotes}`\n"
                else:
                    em.description += f"Max Upvotes: `{max_upvotes}` (unchanged)\n"

                self.staff_vote_channel = staff_vote_channel
                self.config["staff_vote_channel_id"] = staff_vote_channel.id
                self.config["max_upvotes"] = max_upvotes

        else:
            if before_enabled != enabled:
                em.description += f"Enabled: `{enabled}`\n"
            else:
                em.description += f"Enabled: `{enabled}` (unchanged)\n"

            self.config["enabled"] = enabled
        
        with open("data/suggestions_config.json", "w") as f:
            json.dump(self.config, f, indent=2)
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}][Suggestions]> Saved config to data/suggestions_config.json.\n")

        return await ctx.send(embed=em, hidden=True)
        

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.client.wait_until_ready()

        if payload.user_id == self.client.user.id:
            return

        if not self.config["enabled"]:
            return

        if self.suggestions_channel.id == payload.channel_id:
            msg = await self.suggestions_channel.fetch_message(payload.message_id)
            if not msg:
                return
                
            reactions = msg.reactions
            total_reactions = {"yes": 0, "no": 0}
            for reaction in reactions:
                if str(reaction.emoji) == "✅":
                    total_reactions["yes"] = reaction.count
                elif str(reaction.emoji) == "❌":
                    total_reactions["no"] = reaction.count

            if total_reactions["yes"] > total_reactions["no"] and total_reactions["yes"] == self.config["max_upvotes"]:
                if len(msg.embeds) <= 0:
                    return
                if (str(msg.embeds[0].color) == "#00ff00") or (str(msg.embeds[0].color) == "#ff0000"):
                    return
                if str(msg.embeds[0].color) != "#ffff00":
                    my_msg = await self.staff_vote_channel.send(embed=msg.embeds[0])
                    await my_msg.add_reaction("✅")
                    await my_msg.add_reaction("❌")
                    em = msg.embeds[0]
                    em.color = self.client.warn
                    await msg.edit(embed=em)
            

def setup(client):
    client.add_cog(Suggestions(client))
    