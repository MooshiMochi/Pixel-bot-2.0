import json
import re
from datetime import datetime
from constants import const

import discord
import emoji as emojo
from discord.ext import commands, tasks
from discord.ext.commands import EmojiConverter

from discord_slash import cog_ext
from discord_slash.utils import manage_commands

from constants import const

e_conv = EmojiConverter()


class url(str):
    def __init__(self, link):

        if not link:
            self.link = "None"
        else:
            check = re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", link)
            if check:
                link = str(link).replace(".webm", ".png")

                if not any([True for ext in [".jpg", "jpeg", ".png", ".gif"] if ext in str(link)]):

                    self.link = "None"
                else:
                    self.link = link
            else:
                self.link = "None"

    def __str__(self):
        return str(self.link)

    def __repr__(self):
        return f"url(link='{str(self.link)}')"


class ReactionRoles(commands.Cog, name="Reaction Roles"):
    """Create a reaction roles system for your server."""
    
    def __init__(self, client):
        self.client = client

        with open("data/reactions_db.json", "r") as f:
            self.data = json.load(f)

        if not self.data:
            self.data = {}

        self.reaction_remove_ignore_queue = []

        self.save_reaction_data.start()

    @tasks.loop(minutes=1)
    async def save_reaction_data(self):
        await self.client.wait_until_ready()

        with open("data/reactions_db.json", "w") as f:
            json.dump(self.data, f, indent=2)


    @cog_ext.cog_slash(name="rr_msg", guild_ids=[const.guild_id], description="Create a new reaction roles message",
    options=[
        manage_commands.create_option(
            name="send_as_embed", description="Choose whether the message should be in an embed or not.", option_type=3, required=True, choices=[
                manage_commands.create_choice(value="True", name="Yes"),
                manage_commands.create_choice(value="False", name="No")]),
        
        manage_commands.create_option(name="title", description="Set the title for the reaction role message. (Ignore if you don't want a title.)", option_type=3, required=False)
    ])
    @commands.guild_only()
    async def rr_msg(self, ctx, send_as_embed: str = None, title: str = None):
        """Create a new message for reaction roles."""

        await ctx.defer(hidden=True)
        await ctx.send("Success!", hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("Why are you even trying to use this.😐")
            return

        if send_as_embed == "True":
            em = discord.Embed(color=0x8b46d3)

            em.set_footer(icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)),
                          text=ctx.guild.name)
            em.timestamp = datetime.utcnow()

            if title:
                em.title = str(title)
            
            msg = await ctx.channel.send(embed=em)
        
        else:
            if title:
                msg = await ctx.channel.send(str(title))
            
            else:
                msg = await ctx.channel.send("\u200b")

        if str(ctx.channel.id) not in self.data.keys():
            self.data[str(ctx.channel.id)] = {}

        self.data[str(ctx.channel.id)][str(msg.id)] = {"config": 0}

            

    @cog_ext.cog_slash(name="delete_msg", guild_ids=[const.guild_id], description="Delete a reaction roles message",
    options=[
        manage_commands.create_option(name="message_id", description="The ID of the reaction roles message", option_type=3, required=True)
    ])
    async def delete_msg(self, ctx, message_id: str = None):

        await ctx.defer(hidden=True)

        if not message_id:
            return await ctx.send("You did not specify a message ID to delete.", hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("Why are you even trying to use this.😐", hidden=True)
            return

        message_id = str(message_id)

        for ch_id, messages in self.data.copy().items():
            for msg_id in messages.keys():

                if msg_id == str(message_id):
                    ch = ctx.guild.get_channel(int(ch_id))
                    msg = await ch.fetch_message(int(msg_id))
                    del self.data[ch_id][msg_id]
                    await msg.delete()
                    return await ctx.send("Message deleted successfully!", hidden=True)
        else:
            return await ctx.send("I haven't found any messages with that ID. Please check and try again.", hidden=True)

    @cog_ext.cog_slash(name="set_img", guild_ids=[const.guild_id], description="Set an image for a reaction roles message",
    options=[
        manage_commands.create_option(name="message_id", description="The ID of the reaction roles message", option_type=3, required=True),
        manage_commands.create_option(name="url", description="The URL of the image", option_type=3, required=True)
    ])
    @commands.guild_only()
    async def set_img(self, ctx, message_id: str = None, url: url = None):

        await ctx.defer(hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("Why are you even trying to use this.😐", hidden=True)
            return

        if not message_id:
            return await ctx.send("You did not specify a message ID.", hidden=True)

        if (
                not url
                or url in ["None"]
        ):
            return await ctx.send("You did not specify an image url.", hidden=True)

        message_id = str(message_id)

        for ch_id, messages in self.data.items():
            for msg_id in messages.keys():

                if msg_id == message_id:
                    ch = ctx.guild.get_channel(int(ch_id))
                    msg = await ch.fetch_message(int(msg_id))
                    if len(msg.embeds) < 1:
                        return await ctx.send("Cannot use this command on a reaction role menu that doesn't use an embed.", hidden=True)
                    em = msg.embeds[0]
                    em.set_image(url=url)

                    await msg.edit(embed=em)

                    return await ctx.send("Image set", hidden=True)
        else:
            return await ctx.send("I haven't found any messages with that ID. Please check and try again.", hidden=True)

    @cog_ext.cog_slash(name="add_rr", guild_ids=[const.guild_id], description="Add a reaction role to a reaction roles message",
    options=[
        manage_commands.create_option(name="message_id", description="The ID of the reaction roles message", required=True, option_type=3),
        manage_commands.create_option(name="role", description="The role to give when the user reacts", option_type=8, required=True),
        manage_commands.create_option(name="emoji", description="The emoji people will react to and receive the role", option_type=3, required=True),
        manage_commands.create_option(name="description", description="The description of the reaction role entry", option_type=3,
        required=True)
    ])
    @commands.guild_only()
    async def add_rr(self, ctx, message_id:str = None, role:discord.Role = None, emoji:str=None, description:str = None):

        await ctx.defer(hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("Why are you even trying to use this.😐", hidden=True)
            return

        if role.is_bot_managed():
            return await ctx.send("I cannot add that as a reaction role as it is managed by a robot.", hidden=True)
        
        elif role.is_integration():
            return await ctx.send("I cannot add that as a reaction role as it is managed by an integration.", hidden=True)

        elif role.is_default():
            return await ctx.send("I cannot add that as a reaction role as it is a 'default'.", hidden=True)

        elif ctx.guild.roles.index(role) >= ctx.guild.roles.index(ctx.guild.me.top_role):
                return await ctx.send("Unfortunatelly I do not have enough permissiosn to manage that role.", hidden=True)

        message_id = str(message_id)
        ch = None
        msg = None
        for ch_id, messages in self.data.items():
            for msg_id in messages.keys():

                if msg_id == message_id:
                    ch = ctx.guild.get_channel(int(ch_id))
                    msg = await ch.fetch_message(int(msg_id))
                    break

        if not msg:
            return await ctx.send("That message ID doesn't exist. Please check and try again.", hidden=True)

        _unicode = False

        try:
            emoji = await e_conv.convert(ctx, emoji)
        except discord.ext.commands.errors.EmojiNotFound:
            if emojo.emoji_count(emoji) > 0:
                _unicode = True
            else:
                await ctx.send("There is no such emoji in this server!", hidden=True)
                return

        if not _unicode:
            emoji_str = str(emoji)
        else:
            emoji_str = emoji

        desc = msg.embeds[0].description if len(msg.embeds) >= 1 else msg.content

        if desc == discord.Embed.Empty:
            desc = f"{emoji_str} - {description}"
        else:
            desc += f"\n{emoji_str} - {description}"

        if len(msg.embeds) >= 1:
            em = msg.embeds[0]
            em.description = desc

        if str(emoji) in [str(r) for r in msg.reactions]:
            return await ctx.send("That emoji is already in use, please choose another emoji!", hidden=True)

        self.data[str(ch.id)][str(msg.id)][emoji_str] = role.id

        if len(msg.embeds) >= 1:
            await msg.edit(embed=em)
        else:
            await msg.edit(content=desc)

        await msg.add_reaction(emoji)
        return await ctx.send("Reaction role menu updated", hidden=True)

    @cog_ext.cog_slash(name="remove_rr", guild_ids=[const.guild_id], description="Remove a reaction role to a reaction roles message",
    options=[
        manage_commands.create_option(name="message_id", description="The ID of the reaction roles message", option_type=3, required=True),
        manage_commands.create_option(name="emoji", description="The emoji corresponding to the reaction role", option_type=3, required=True)
    ])
    @commands.guild_only()
    async def remove_rr(self, ctx, message_id: str = None, emoji: str = None):

        await ctx.defer(hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            return await ctx.send("Why are you even trying to use this.😐")

        message_id = str(message_id)
        ch = None
        msg = None
        em = None
        for ch_id, messages in self.data.items():
            for msg_id in messages.keys():

                if msg_id == str(message_id):
                    ch = ctx.guild.get_channel(int(ch_id))
                    msg = await ch.fetch_message(int(msg_id))
                    break

        if not msg:
            return await ctx.send("That message ID doesn't exist. Please check and try again.", hidden=True)

        if len(msg.embeds) >= 1:
            em = msg.embeds[0]
            entries = em.description.split("\n")
        else:
            entries = msg.content.split("\n")

        _unicode = False

        try:
            emoji = await e_conv.convert(ctx, emoji)
        except discord.ext.commands.errors.EmojiNotFound:
            if emojo.emoji_count(emoji) > 0:
                _unicode = True
            else:
                return await ctx.send("There is no such emoji in this server!", hidden=True)

        if not _unicode:
            emoji_str = str(emoji)
        else:
            emoji_str = emoji

        if emoji_str not in [str(e) for e in msg.reactions]:
            return await ctx.send("That reaction role doesn't exist.", hidden=True)

        if emoji_str in msg.content:
            entries = [x for x in entries if emoji_str not in x]
            # entries.pop(reaction_number - 1)
            new_desc = "\n".join(entries)
        
        try:
            del self.data[str(ch.id)][str(msg.id)][emoji_str]
        except KeyError:
            return await ctx.send("Reaction Role could not be found in the database, but it was removed from the embed.", hidden=True)

        msg_reactions = msg.reactions
        for reaction in msg_reactions:
            if str(reaction.emoji) == emoji_str:
                users = await reaction.users().flatten()
                for user in users:
                    await reaction.remove(user)
                break

        if len(msg.embeds) >= 1:
            em.description = new_desc
            await msg.edit(embed=em)
        else:
            if emoji_str in msg.content:
                await msg.edit(content=new_desc)

        await ctx.send("Success!", hidden=True)


    @cog_ext.cog_slash(name="rr_config", guild_ids=[const.guild_id], description="Configure a reaction roles message",
    options=[
        manage_commands.create_option(name="message_id", description="The ID of the reaction roles message", option_type=3, required=True),
        manage_commands.create_option(
            name="type", description="The type of configuration to set for the embed", option_type=4, required=True, choices=[
                manage_commands.create_choice(value=0, name="Remove and add roles (default)"),
                manage_commands.create_choice(value=1, name="Remove role only"),
                manage_commands.create_choice(value=2, name="Add role only"),
                manage_commands.create_choice(value=3, name="Can obtain only 1 role")]),

    ])
    @commands.guild_only()
    async def rr_config(self, ctx, message_id: str = None, type: int = None):
        
        await ctx.defer(hidden=True)

        if not ctx.author.guild_permissions.manage_emojis:
            await ctx.send("Why are you even trying to use this.😐", hidden=True)
            return

        ch = None
        msg = None
        for ch_id, messages in self.data.items():
            for msg_id in messages.keys():

                if msg_id == str(message_id):
                    ch = ctx.guild.get_channel(int(ch_id))
                    msg = await ch.fetch_message(int(msg_id))
                    if msg:
                        self.data[ch_id][msg_id]["config"] = int(type)
                        return await ctx.send(f"Reaction message set to: {type}: {const.rr_type_config[type]}", hidden=True)

        if not msg:
            return await ctx.send("That message ID doesn't exist. Please check and try again.", hidden=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.client.wait_until_ready()  # Wait for the client to be ready before doing this to prevent errors.

        try:
            if self.client.get_user(payload.user_id).bot:
                return
            else:

                try:
                    config = self.data[str(payload.channel_id)][str(payload.message_id)]["config"]
                except KeyError:  # No such reaction roles is registered.
                    try:
                        self.data[str(payload.channel_id)][str(payload.message_id)]["config"] = 0
                    except KeyError:
                        return

                member = payload.member
                channel = member.guild.get_channel(int(payload.channel_id))

                if config == 1:  # Remove only.
                    return

                role = payload.member.guild.get_role(
                    int(
                        self.data[str(payload.channel_id)]
                        [str(payload.message_id)]
                        [str(payload.emoji)]))
                if role:
                    if config == 1:  # Remove only.
                        if role not in member.roles:
                            return
                        return await member.remove_roles(role)

                    elif config == 3:  # Restrict to 1 role.

                        if role in member.roles:
                            return
                        await member.add_roles(role)

                        msg = await channel.fetch_message(payload.message_id)

                        for reaction in msg.reactions:
                            if str(payload.emoji) == str(reaction):
                                continue

                            role_id = int(self.data[str(msg.channel.id)][str(msg.id)][str(reaction)])
                            remove_role = payload.member.guild.get_role(role_id)
                            await reaction.remove(payload.member)
                            await payload.member.remove_roles(remove_role)

                    else:
                        if role in member.roles:
                            return
                        await member.add_roles(role)
                else:
                    await channel.send(
                        f"Role `{int(self.data[str(payload.channel_id)][str(payload.message_id)][str(payload.emoji)])}` not found!")

        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.client.wait_until_ready()

        if payload.user_id in self.reaction_remove_ignore_queue:
            self.reaction_remove_ignore_queue.remove(payload.user_id)
            return

        try:
            if self.client.get_user(payload.user_id).bot:
                return
            else:
                try:
                    config = self.data[str(payload.channel_id)][str(payload.message_id)]["config"]
                except KeyError:  # No such reaction roles is registered.
                    try:
                        self.data[str(payload.channel_id)][str(payload.message_id)]["config"] = 0
                    except KeyError:
                        return
                try:
                    guild = self.client.get_guild(payload.guild_id)
                except AttributeError:
                    return print(
                        "There was an error while trying to get the guild from 'payload.member' in line 467 in reaction_roles.py")

                try:
                    channel = guild.get_channel(payload.channel_id)
                except AttributeError:
                    return print("There was an error while trying to get the channel on line 472 in reaction_roles.py")

                role = guild.get_role(
                    int(
                        self.data[str(payload.channel_id)]
                        [str(payload.message_id)]
                        [str(payload.emoji)]))
                if role:
                    member = guild.get_member(payload.user_id)
                    if member:
                        if config == 2:  # Add role only.
                            if role in member.roles:
                                return
                            return await member.add_roles(role)

                        if role not in member.roles:
                            return

                        await member.remove_roles(role)
                    else:
                        await channel.send("Member not found!")
                else:
                    await channel.send("Role not found!")
        except KeyError:
            pass


def setup(client):
    client.add_cog(ReactionRoles(client))