from datetime import datetime
from discord import Embed, Member, Role, AllowedMentions
from discord.ext import commands

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from constants import const


class Miscellaneous(commands.Cog):
    def __init__(self, client):
        self.client = client

    
    @cog_slash(name="avatar", description="Show the avatar of a user", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The memebr to show the avatar picture of", option_type=6, required=False) | {"focused": True}
    ])
    async def avatar(self, ctx:SlashContext, member:Member=None):
        
        await ctx.defer(hidden=True)

        if not member:
            member = ctx.author

        em = Embed(title="Avatar", color=self.client.failure)
        em.set_author(name=f"{member.name}#{member.discriminator}", icon_url=member.avatar_url_as(static_format="png", size=4096))
        em.set_image(url=member.avatar_url_as(static_format="png", size=4096))
        await ctx.embed(embed=em, footer="Miscellaneous")

    
    @cog_slash(name="embed", description="Create an embed", guild_ids=const.slash_guild_ids, options=[
        create_option("send_hidden", "Send the embed ephemerally or not", 5, False),
        create_option("title", "The title field", 3, False),
        create_option("desc", "The description field", 3, False),
        create_option("color", "The embed color (must be in HEX: #ff00ff)", 3, False),
        create_option("footer", "The footer of the embed", 3, False),
        create_option("footer_icon_url", "The icon that appears at the footer", 3, False),
        create_option("thumbnail_url", "The thumbnail for the embed (Must be an URL)", 3, False),
        create_option("author", "The author field of the embed", 3, False),
        create_option("author_url", "The url that users will be redirected to once they click the author field", 3, False),
        create_option("author_icon_url", "The icon that will appear in the autor field", 3, False),
        create_option("timestamp", "Whether to have an embed timestamp or not", 5, False),
        create_option("image_url", "Whether to have an image in the emebd (max 1) (must be URL)", 3, False),
        create_option("field_1", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_2", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_3", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_4", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_5", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_6", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_7", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_8", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_9", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("field_10", "Please specify the name and value separated by | . Eg: field name | field value", 3, False),
        create_option("optional_ping", "Ping a role when this embed is sent", 8, False)
    ])
    async def embed(self, ctx:SlashContext, send_hidden:bool=True, title:str=None, desc:str=None, color:str=None, footer:str=None, footer_icon_url:str=None, thumbnail_url:str=None, author:str=None, author_url:str=None, author_icon_url:str=None, timestamp:bool=False, image_url:str=None, field_1:str=None, field_2:str=None, field_3:str=None, field_4:str=None, field_5:str=None, field_6:str=None, field_7:str=None, field_8:str=None, field_9:str=None, field_10:str=None, optional_ping:Role=None):
        await ctx.defer(hidden=send_hidden)

        if color:
            color = color.replace("#", "0x")
            if not color.startswith("0x"):
                color = "0x" + color

            try:
                color=int(color, 16)
            except ValueError:
                color = Embed.Empty
        else:
            color = Embed.Empty
            
        em = Embed(title=title if title else "", description=desc if desc else "\u200b", color=color)
        em.set_footer(text=footer if footer else "", icon_url=footer_icon_url if footer_icon_url else "")
        em.set_thumbnail(url=thumbnail_url) if thumbnail_url else None
        em.set_author(name=author if author else "", url=author_url if author_url else "", icon_url=author_icon_url if author_icon_url else "")
        em.set_image(url=image_url) if image_url else None
        if timestamp:
            em.timestamp = datetime.utcnow()
        
        for field_str in (field_1, field_2, field_3, field_4, field_5, field_6, field_7, field_8, field_9, field_10):
            if field_str is None:
                continue

            temp = field_str.split("|")
            if len(temp) <= 1:
                em.add_field(name=temp[0], value="\u200b", inline=False)
            else:
                em.add_field(name=temp[0], value=temp[1], inline=False)

        send_settings = {
            "hidden": send_hidden,
        }
        if optional_ping:
            role = ctx.guild.get_role(optional_ping.id if not isinstance(optional_ping, int) else optional_ping)
            send_settings["content"] = role.mention if role else "@Role Not Found"
        
        send_settings["embed"] = em

        return await ctx.send(**send_settings, allowed_mentions=AllowedMentions(roles=True if ctx.author.guild_permissions.manage_roles else False))

    

def setup(client):
    client.add_cog(Miscellaneous(client))
    