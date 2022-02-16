import uuid
import discord
import random
import asyncio

from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component

from datetime import datetime

from constants import const


class WhackABrick(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.emojis = {}

        self.getting_ready.start()
        "<:stone_brick:943230164362485760>"
        "<:mossy_brick:943230816505454612>"
        "<:stone:943230601232793680>"

    @tasks.loop(count=1)
    async def getting_ready(self):
        guild = self.client.get_guild(const.guild_id)
        for emoji in guild.emojis:
            if emoji.name == "stone_brick" and emoji.id == 943230164362485760:
                self.emojis["brick"] = emoji
            elif emoji.name == "mossy_brick" and emoji.id == 943230816505454612:
                self.emojis["moss"] = emoji
            elif emoji.name == "stone" and emoji.id == 943230601232793680:
                self.emojis["stone"] = emoji
        if len(self.emojis) < 3:
            self.client.logger.error("Extension whack_a_brick.py was unloaded because the required emoji were not found.")
            self.client.unload_extension("commands.games.whack_a_brick")

    @getting_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()

    async def clean_bg(self):
        emoji = self.emojis["brick"]
        rows = []
        for _ in range(4):
            buttons = []
            for _ in range(5):
                btn = create_button(emoji=emoji,
                custom_id=f"wab_clean_{uuid.uuid4()}",
                style=ButtonStyle.grey, 
                disabled=True)
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return rows

    async def random_moss(self, level):
        moss = self.emojis["moss"]
        brick = self.emojis["brick"]
        coords = []
        for _ in range((level // 5) + 1):
            coords.append((random.randint(0, 4), random.randint(0, 3)))

        coords = coords[:10]
        
        rows = []
        for y in range(4):
            buttons = []
            for x in range(5):
                btn = create_button(emoji=moss if (x, y) in coords else brick,
                custom_id=f"wab_moss_{uuid.uuid4()}_{x}{y}" if (x, y) in coords else f"wab_clean_{uuid.uuid4()}",
                style=ButtonStyle.green if (x, y) in coords else ButtonStyle.grey,
                )
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return (rows, coords)

    async def brick_ingot(self, coords:list, clicked_coords:list):
        brick = self.emojis["brick"]
        stone = self.emojis["stone"]
        moss = self.emojis["moss"]
        rows = []
        for y in range(4):
            buttons = []
            for x in range(5):
                btn = create_button(
                    emoji=stone if (x, y) in clicked_coords else brick if (x, y) not in coords else moss,
                    custom_id=f"wab_stone_{uuid.uuid4()}" if (x, y) in clicked_coords else f"wab_clean_{uuid.uuid4()}" if (x, y) not in coords else f"wab_moss_{uuid.uuid4()}_{x}{y}",
                    style=ButtonStyle.blue if (x, y) in clicked_coords else ButtonStyle.grey if (x, y) not in coords else ButtonStyle.green,
                    disabled=True if (x, y) in clicked_coords or len(coords) == len(clicked_coords) else False
                )
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return rows

    async def run_game(self, ctx:SlashContext):
        components = await self.clean_bg()
        level = 1
        clicked_coords = []
        msg = await ctx.send("__**Level 1**__", components=components)
        await asyncio.sleep(5)
        
        components, coords = await self.random_moss(level)
        await msg.edit(content=f"__**Level {level}**__", components=components)
        level_ts = datetime.utcnow().timestamp()

        while 1:
            try:
                button_ctx: ComponentContext = await wait_for_component(self.client, components=components, timeout=5)
                
                if button_ctx.author_id != ctx.author_id:
                    await button_ctx.send("You cannot do that. Start your own game with `/whack_a_brick`.", hidden=True)
                    continue

                _id = str(button_ctx.custom_id)
                if _id.startswith("wab_moss_"):
                    if datetime.utcnow().timestamp() - level_ts >= 5:
                        raise asyncio.TimeoutError

                    clicked_coords.append((int(_id[-2]), int(_id[-1])))
                    components = await self.brick_ingot(coords, clicked_coords)
                    await button_ctx.edit_origin(content=f"__**Level {level}**__", components=components)
                    if len(clicked_coords) == len(coords):
                        level += 1
                        clicked_coords = []
                        await asyncio.sleep(3)
                        components, coords = await self.random_moss(level)
                        await msg.edit(content=f"__**Level {level}**__", components=components)
                        level_ts = datetime.utcnow().timestamp() + 2
                        continue
                else:
                    raise asyncio.TimeoutError

            except asyncio.TimeoutError:
                em = discord.Embed(title="You lost!", description=f"**You got to level {level} 🎉**\n> You won: {int(1000*(1.05**(level-1)))}💸", color=self.client.failure)
                em.set_thumbnail(url=ctx.author.avatar_url_as(static_format="png", size=4096))
                em.set_footer(text="TN | Whack A Brick", icon_url=self.client.png)

                await self.client.addcoins(ctx.author_id, 1000*(1.05**(level-1)), f"Got to level {level} in whack_a_brick.")
                await msg.edit(embed=em, components=[])
                return

    @cog_slash(name="whack_a_brick", description="Start a 'whack a brick' game", guild_ids=const.slash_guild_ids)
    @commands.cooldown(10, 300, commands.BucketType.user)
    async def whack_a_brick(self, ctx:SlashContext):
        em = discord.Embed(title="How to play!", description="Welcome to **Whack a brick**!\n\nThis game is simple. After 5 seconds of the command running, a random\nmossy block will appear on one of the squares.\nYou have to click on it, but be quick as you only have 5 seconds.\nThe more levels you pass, the higher your overall reward in the end.\n\n**Good luck!**", color=self.client.success)
        em.set_footer(text="TN | Whack A Brick", icon_url=self.client.png)
        await ctx.send(embed=em, hidden=True)

        self.client.loop.create_task(self.run_game(ctx))


def setup(client):
    client.add_cog(WhackABrick(client=client))
