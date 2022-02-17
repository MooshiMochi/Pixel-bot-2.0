import uuid
import discord
import random
import asyncio

from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.model import ButtonStyle, BucketType
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
            elif emoji.name == "sus_brick" and emoji.id == 943497488122392586:
                self.emojis["sus"] = emoji

        if len(self.emojis) < 3:
            self.client.logger.error("Extension whack_a_brick.py was unloaded because the required emoji were not found.")
            self.client.unload_extension("commands.games.whack_a_brick")

    @getting_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()

    async def troll_screen(self):
        brick = self.emojis["brick"]
        moss = self.emojis["moss"]

        rows = []
        coords = []
        for x in range(random.randint(5, 12)):
            new_coord = (random.randint(0, 4), random.randint(0, 3))
            coords.append(new_coord)
            while 1:
                if coords.count(new_coord) > 1:
                    coords.pop(-1)
                    new_coord = (random.randint(0, 4), random.randint(0, 3))
                    coords.append(new_coord)
                else:
                    break

        for y in range(4):
            buttons = []
            for x in range(5):
                btn = create_button(
                    custom_id=f"wab_troll_{uuid.uuid4()}",
                    style=ButtonStyle.green if (x, y) in coords else ButtonStyle.grey,
                    emoji=moss if (x, y) in coords else brick,
                    disabled=True
                )
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return rows
        
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


    async def custom_bg(self, style, emoji):
        emoji = emoji
        rows = []
        for _ in range(4):
            buttons = []
            for _ in range(5):
                btn = create_button(
                    custom_id=f"wab_red_{uuid.uuid4()}",
                    style=style,
                    disabled=True,
                    emoji=emoji
                )
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return rows


    async def random_moss(self, level):
        moss = self.emojis["moss"]
        brick = self.emojis["brick"]
        sus = self.emojis["sus"]

        extra_coord = ()
        extra_emot = None

        _choice = random.randint(1, 5)
        if _choice == 3:
            extra_emot = random.choice(("cash", "bomb", "hide", "moyai"))

        coords = []
        for _ in range((level // (random.choice((3, 8)))) + 1):
            new_coord = (random.randint(0, 4), random.randint(0, 3))
            coords.append(new_coord)
            while 1:
                if coords.count(new_coord) > 1:
                    coords.pop(-1)
                    new_coord = (random.randint(0, 4), random.randint(0, 3))
                    coords.append(new_coord)
                else:
                    break

        coords = coords[:12]
        sus_coords = []
        sus_coords_num = int(0.5*len(coords)) if len(coords) >= 3 else 0
        if sus_coords_num >= 1:
            coords = coords[:-sus_coords_num]

        if sus_coords_num >= 1:
            while 1:
                sus_coord = (random.randint(0, 4), random.randint(0, 3))
                if sus_coord not in coords and sus_coord not in sus_coords:
                    sus_coords.append(sus_coord)

                if len(sus_coords) == sus_coords_num:
                    break
                continue

        if extra_emot:
            while 1:
                extra_coord = (random.randint(0, 4), random.randint(0, 3))
                if extra_coord not in coords and extra_coord not in sus_coords:
                    break
                continue


        rows = []
        for y in range(4):
            buttons = []
            for x in range(5):
                if (x, y) in coords:
                    emoji = moss
                    custom_id = f"wab_moss"
                    style = ButtonStyle.green

                elif (x, y) in sus_coords:
                    emoji = sus
                    custom_id = f"wab_moss_sus"
                    style = ButtonStyle.green

                elif extra_coord and (x, y) == extra_coord:
                    if extra_emot == "cash":
                        emoji = moss
                        custom_id = f"wab_moss_cash"
                        style = ButtonStyle.green

                    elif extra_emot == "bomb":
                        emoji = moss
                        custom_id = f"wab_moss_bomb"
                        style = ButtonStyle.green

                    elif extra_emot == "hide":
                        emoji = moss
                        custom_id = f"wab_moss_hide"
                        style = ButtonStyle.green

                    elif extra_emot == "moyai":
                        emoji = moss
                        custom_id = f"wab_moss_moyai"
                        style = ButtonStyle.green

                else:
                    emoji = brick
                    custom_id = f"wab_clean"
                    style = ButtonStyle.grey

                btn = create_button(
                    emoji=emoji,    
                    custom_id=f"{custom_id}_{uuid.uuid4()}_{x}{y}",
                    style=style
                )
                buttons.append(btn)
            rows.append(create_actionrow(*buttons))

        return (rows, coords, sus_coords, (extra_coord, extra_emot))

    async def brick_ingot(self, coords:list, sus_coords:list, clicked_coords:list, extra_coord:tuple, _id:str):
        brick = self.emojis["brick"]
        stone = self.emojis["stone"]
        moss = self.emojis["moss"]
        sus = self.emojis["sus"]

        sus_num = 0
        sus_num += len(coords) % 3

        
        if not extra_coord:
            extra_coord = (None, None)

        _clicked_coords = clicked_coords.copy()
        _clicked_coords.remove(extra_coord[0]) if extra_coord[0] in _clicked_coords else None

        rows = []
        for y in range(4):
            buttons = []
            for x in range(5):
                if ((x, y) in clicked_coords) and ((x, y) in coords):
                    emoji = stone
                    custom_id = f"wab_stone"
                    style = ButtonStyle.blue

                elif (x, y) in coords:
                    if extra_coord[0] in clicked_coords and extra_coord[1] == "hide":
                        emoji = sus
                    else:
                        emoji = moss
                    custom_id = f"wab_moss"
                    style = ButtonStyle.green

                elif ((x, y) in sus_coords) and ((x, y) not in clicked_coords):
                    emoji = sus
                    custom_id = f"wab_moss_sus"
                    style = ButtonStyle.green

                elif ((x, y) in sus_coords) and ((x, y) in clicked_coords):
                    emoji = sus
                    custom_id = f"wab_moss_sus"
                    style = ButtonStyle.danger
                
                else:
                    emoji = brick
                    custom_id = f"wab_clean"
                    style = ButtonStyle.grey
                
                if ((x, y) == extra_coord[0]) and ((x, y) not in clicked_coords):
                    if extra_coord[1] == "cash":
                        emoji = moss
                        custom_id = f"wab_moss_cash"
                        style = ButtonStyle.green

                    elif extra_coord[1] == "bomb":
                        emoji = moss
                        custom_id = f"wab_moss_bomb"
                        style = ButtonStyle.green

                    elif extra_coord[1] == "moyai":
                        emoji = moss
                        custom_id = f"wab_moss_moyai"
                        style = ButtonStyle.green

                    elif extra_coord[1] == "hide":
                        emoji = moss
                        custom_id = f"wab_moss_hide"
                        style = ButtonStyle.green

                if (x, y) == extra_coord[0] and (
                    ((x, y) in clicked_coords) or (len(_clicked_coords) == len(coords))
                    ):

                    if extra_coord[1] == "cash":
                        emoji = "💷"
                        custom_id = f"wab_moss_cash"
                        style = ButtonStyle.blue

                    elif extra_coord[1] == "bomb":
                        emoji = "💣"
                        custom_id = f"wab_moss_bomb"
                        style = ButtonStyle.red

                    elif extra_coord[1] == "moyai":
                        emoji = "🗿"
                        custom_id = f"wab_moss_moyai"
                        style = ButtonStyle.red

                    elif extra_coord[1] == "hide":
                        emoji = "🕳️"
                        custom_id = f"wab_moss_hide"
                        style = ButtonStyle.red


                if ((x, y) in clicked_coords) or (len(_clicked_coords) == len(coords)):
                    disabled = True
                else:
                    disabled = False

                if extra_coord[0] in clicked_coords and extra_coord[1] == "bomb":
                    if ((x, y) in coords) or ((x, y) in sus_coords) or ((x, y) == extra_coord[0]):
                        style = ButtonStyle.red
                    else:
                        style = ButtonStyle.grey

                    custom_id = f"wab_moss_bomb"
                    disabled = True

                btn = create_button(
                    emoji=emoji,
                    custom_id=f"{custom_id}_{uuid.uuid4()}_{x}{y}",
                    style=style,
                    disabled=disabled
                )

                buttons.append(btn)
            rows.append(create_actionrow(*buttons))
        return rows

    async def run_game(self, ctx:SlashContext):
        components = await self.client.loop.create_task(self.clean_bg())
        level = 1
        prize_multiplier = 1
        clicked_coords = []
        sus_brick_hit = False
        msg = await ctx.send("__**Level 1**__", components=components)
        await asyncio.sleep(2)
        await msg.edit(content="__**Level 1**__", components=await self.client.loop.create_task(self.troll_screen()))
        await asyncio.sleep(1)
        await msg.edit(content="__**Level 1**__", components=components)
        await asyncio.sleep(2)

        components, coords, sus_coords, extra_coord = await self.client.loop.create_task(self.random_moss(level))
        await msg.edit(content=f"__**Level {level}**__", components=components)
        level_ts = datetime.utcnow().timestamp()

        while 1:
            try:
                button_ctx: ComponentContext = await wait_for_component(self.client, components=components, timeout=17)
                
                if button_ctx.author_id != ctx.author_id:
                    await button_ctx.send("You cannot do that. Start your own game with `/whack_a_brick`.", hidden=True)
                    continue

                _id = str(button_ctx.custom_id)
                if _id.startswith("wab_moss_"):

                    if datetime.utcnow().timestamp() - level_ts >= 5:
                        raise asyncio.TimeoutError("-Out of time!")

                    clicked_coords.append((int(_id[-2]), int(_id[-1])))

                    if _id.startswith("wab_moss_moyai"):
                        win_probability = 315
                        if random.randint(1, 500) != win_probability:
                            await ctx.send("***Tiki.. tiki... tiki....***", hidden=True)

                            level += 1
                            clicked_coords = []
                            await button_ctx.edit_origin(components=await self.client.loop.create_task(self.custom_bg(ButtonStyle.blue, "🟨")))
                            await asyncio.sleep(1.5)
                            components, coords, sus_coords, extra_coord = await self.client.loop.create_task(self.random_moss(level))
                            try:
                                await msg.edit(content=f"__**Level {level}**__", components=components)
                            except discord.NotFound:
                                raise asyncio.TimeoutError("-Game message was deleted 'w'")

                            level_ts = datetime.utcnow().timestamp() + 2
                            continue
                        
                        else:
                            await button_ctx.edit_origin(components=await self.client.loop.create_task(self.custom_bg(ButtonStyle.red, "💥")))
                            await asyncio.sleep(1.5)
                            raise asyncio.TimeoutError("-You are extremely unlucky. It was 1 in 500 chance to lose and you took it head on.")


                    components = await self.client.loop.create_task(self.brick_ingot(coords, sus_coords, clicked_coords, extra_coord, _id))
                    
                    try:
                        await button_ctx.edit_origin(content=f"__**Level {level}**__", components=components)
                    except discord.NotFound:
                        raise asyncio.TimeoutError("-Game message was deleted 'w'")

                    if _id.startswith("wab_moss_sus_"):
                        sus_brick_hit = True
                        raise asyncio.TimeoutError(random.choice(['-How sus! You hit a susbrick and lost all of your winnings on this round.', '-Oh no! You hit a susbrick by mistake and it cost you the game. ', '-Sus! You hit a susbrick and lost the game.']))
                    elif _id.startswith("wab_moss_cash_"):
                        await ctx.send("You have just doubled your earnings!", hidden=True)
                        prize_multiplier *= 2
                                                
                    elif _id.startswith("wab_moss_hide_"):
                        await ctx.send("You have stumbled upon a trap. Try to guess correct bricks by memory!", hidden=True)

                    elif _id.startswith("wab_moss_bomb_"):
                        await ctx.send("Hey, looks like this blew up all the bricks for you! Nice one.", hidden=True)
                    _clicked_coords = clicked_coords.copy()
                    _clicked_coords.remove(extra_coord[0]) if extra_coord[0] in _clicked_coords else None
                    if len(_clicked_coords) == len(coords) or _id.startswith("wab_moss_bomb_"):
                        
                        level += 1
                        clicked_coords = []
                        await asyncio.sleep(1.5)
                        components, coords, sus_coords, extra_coord = await self.client.loop.create_task(self.random_moss(level))
                        try:
                            await msg.edit(content=f"__**Level {level}**__", components=components)
                        except discord.NotFound:
                            raise asyncio.TimeoutError("-Game message was deleted 'w'")

                        level_ts = datetime.utcnow().timestamp() + 2
                        continue
                else:
                    raise asyncio.TimeoutError("-Incorrect Brick!")

            except asyncio.TimeoutError as error:

                await ctx.send(str(error)[1:] if str(error).startswith("-") else "Out of time!", hidden=True)
                win = 0
                if level > 1:
                    win = 1000*(1.15**level) * prize_multiplier
                if sus_brick_hit:
                    win = 0
                em = discord.Embed(title="You lost!", description=f"**You got to level {level} 🎉**\n> You won: {int(win)}💸\n> Prize Multiplier: {int(prize_multiplier)}", color=self.client.failure)
                em.set_thumbnail(url=ctx.author.avatar_url_as(static_format="png", size=4096))
                em.set_footer(text="TN | Whack A Brick", icon_url=self.client.png)

                if level > 1:
                    await self.client.addcoins(ctx.author_id, win, f"Got to level {level} in whack_a_brick.")
                await asyncio.sleep(3) if "sus" in str(error) else None 
                try:
                    await msg.edit(embed=em, components=[])
                except discord.NotFound:
                    return
                return

    @cog_slash(name="whack_a_brick", description="Start a 'whack a brick' game", guild_ids=const.slash_guild_ids)
    @commands.cooldown(10, 60*60, BucketType.member)
    async def whack_a_brick(self, ctx:SlashContext):
        await self.client.wait_until_ready()
        em = discord.Embed(title="How to play!", description=f"Welcome to **Whack a brick**!\n\nThis game is simple. After 5 seconds of the command running, a random\nmossy block will appear on one of the squares.\nYou have to click on it, but be quick as you only have 5 seconds.\nThe more levels you pass, the higher your overall reward in the end.\n\n**Good luck!**\n\n*Do not hit the sus bricks as they will make you lose!* {self.emojis['sus']}", color=self.client.success)
        em.set_footer(text="TN | Whack A Brick", icon_url=self.client.png)
        await ctx.send(embed=em, hidden=True)

        self.client.loop.create_task(self.run_game(ctx))


def setup(client):
    client.add_cog(WhackABrick(client=client))
