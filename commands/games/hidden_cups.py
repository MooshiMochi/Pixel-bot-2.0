import json
import discord
import asyncio

from random import shuffle

from uuid import uuid4

from datetime import datetime

from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

from constants import const


class HiddenCups(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.getting_ready.start()
        self.cup_emoji = None

        self.winnings = {}

    @tasks.loop(count=1)
    async def getting_ready(self):
        guild = self.client.get_guild(const.emotes_guild_id)
        for emoji in guild.emojis:
            if emoji.name == "cup" and emoji.id == 951840373557297233:
               self.cup_emoji = emoji
        
        if self.cup_emoji is None:
            self.client.logger.error("Extension hidden_cups.py was unloaded because the required emoji was not found.")
            self.client.unload_extension("commands.games.hidden_cups")

    @getting_ready.before_loop
    async def before_getting_ready(self):
        await self.client.wait_until_ready()

    async def check_user(self, authorid):
        if int(self.client.user.id) == int(authorid):
            return {
                "wallet": 0,
                "bank": 0,
                "inventory": [],
            }
        try:
            return self.client.economydata[str(authorid)]
        except KeyError:
            self.client.economydata[str(authorid)] = {
                "wallet": 0,
                "bank": 10000,
                "inventory": [],
            }
            return self.client.economydata[str(authorid)]


    async def rebuildComponents(self, cups:list=[], gameId:str=None):        
        buttons = []

        for index, cup in enumerate(cups):
            buttons.append(
                create_button(
                    style=ButtonStyle.grey,
                    custom_id=f"HiddenCupsBtn_{gameId}_{cup}_{index}",
                    emoji="💔" if cup == 3 else "💰" if cup == 4 else "☠️" if cup == 5 else self.cup_emoji
                )
            )
        
        return [create_actionrow(*buttons)]

    
    @cog_slash(name="hidden_cups", description="Find the correct cup and get 2x your 💸 bet", guild_ids=const.slash_guild_ids, options=[
        create_option(name="bet", description="The amount of 💸 you would like to bet", option_type=3, required=True)
    ])
    async def hidden_cups(self, ctx:SlashContext, bet:str=None):
        
        
        bet = await self.client.parse_int(bet)

        failure_em = (
            discord.Embed(color=self.client.failure, description="")
            .set_footer(
                text="TN | Hidden Cups", 
                icon_url=self.client.png))

        if bet < 100:
            failure_em.description = "You need at least 100 💸"
            return await ctx.send(embed=failure_em, hidden=True)

        await self.check_user(ctx.author_id)
        
        auth_data = self.client.economydata[str(ctx.author_id)]

        if auth_data["bank"] < bet:
            failure_em.description = "**You don't have enough 💸 in your bank.\nDeposit some from the bank using `/deposit`.**"
            return await ctx.send(embed=failure_em, hidden=True)
        
        data = self.client.wab_data.get(str(ctx.author_id), None)
        if not data:
            data = {
                "ts": datetime.utcnow().timestamp(),
                "attempts": 5}
            self.client.wab_data[str(ctx.author_id)] = data
        
        if datetime.utcnow().timestamp() - data["ts"] >= 24 * 60 * 60:
            self.client.wab_data[str(ctx.author_id)]["attempts"] = 5

        if data["attempts"] == 0:
            __em = discord.Embed(color=self.client.failure, title=f"Free attempts exhausted.", description=f"You have exhausted your daily 5 free attempts.\nIf you wish to play the game, it will cost you {await self.client.round_int(self.client.play_price)}💸. \n\n**Do you wish to proceed?**")
            __em.set_footer(text=f"TN | Hidden Cups", icon_url=self.client.png)

            buttons = [
                create_button(style=ButtonStyle.green, label="Continue", custom_id="yes"),
                create_button(style=ButtonStyle.red, label="Cancel", custom_id="no")
            ]
            ar = [create_actionrow(*buttons)]

            __msg = await ctx.send(embed=__em, components=ar)

            while 1:
                try:
                    button_ctx: ComponentContext = await wait_for_component(self.client, __msg, ar, timeout=10)

                    if ctx.author_id != button_ctx.author_id:
                        await button_ctx.send("You are not the author of this command therefore, you cannot use these interactions.", hidden=True)
                        continue

                    elif button_ctx.custom_id == "yes":
                        
                        try:
                            e = self.client.economydata[str(ctx.author_id)]
                        except KeyError:
                            self.client.economydata[str(ctx.author_id)] = {
                                "wallet": 0,
                                "bank": 10000,
                                "inventory": [],
                            }
                            e = self.client.economydata[str(ctx.author_id)]

                        if e["bank"] < self.client.play_price + bet:
                            err = discord.Embed(color=self.client.failure, description="You are too poor to afford this.\nDeposit some more money into your bank and try again.")
                            err.set_footer(text="TN | Hidden Cups", icon_url=self.client.png)
                            await ctx.send(embed=err, hidden=True)
                            raise asyncio.TimeoutError
                        else:
                            await self.client.addcoins(ctx.author_id, -self.client.play_price, "Purchased 1 play ticket for 'Hidden Cups'")
                        
                        await button_ctx.send(f"You have been charged **__{self.client.play_price}💸__**", hidden=True)
                        try:
                            await __msg.delete()
                        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                            pass
                        break

                    elif button_ctx.custom_id == "no":
                        raise asyncio.TimeoutError

                except asyncio.TimeoutError:
                    try:
                        self.client.slash.commands[ctx.command].reset_cooldown(ctx)
                    except AttributeError:
                        pass

                    try:
                        await __msg.delete()
                    except (discord.HTTPException, discord.NotFound):
                        return
        else:
            if data["attempts"] == 5:
                self.client.wab_data[str(ctx.author_id)]["ts"] = datetime.utcnow().timestamp()
            
            self.client.wab_data[str(ctx.author_id)]["attempts"] -= 1

        user = self.winnings.get(ctx.author_id, None)
        if not user:
            self.winnings[ctx.author_id] = {
                "ts": datetime.utcnow().timestamp(),
                "total": 0
            }
        
        elif datetime.utcnow().timestamp() - user["ts"] >= 24*60*60:
            self.winnings[ctx.author_id]["total"] = 0
            self.winnings[ctx.author_id]["ts"] = datetime.utcnow().timestamp()

        msg = await ctx.send("⌛ Your game is loading...")
        
        await self.client.addcoins(ctx.author_id, -bet, "Bet in `/hidden_cups`")

        gameEnded = False
        gameId = uuid4()

        cups = [0, 1, 2]; shuffle(cups)

        em = discord.Embed(color=self.client.failure, description=f"💸 Your bet: **{int(bet):,}** 💸\n\n📜 Game Rules 📜\n\nHere are 3 cups. Each cup contains a prize, good, bad, and kinda bad! You can win:\n- **1/2 of your bet**\n- **2x your bet**\n- **nothing**.\nYou have one attempt. Good luck and have fun!")
        em.set_footer(text="TN | Hidden Cups", icon_url=self.client.png)
        em.set_author(name="🏆 Hidden Cups")


        components = await self.rebuildComponents(cups, gameId)
        
        await msg.edit(embed=em, components=components, content=None)

        while 1:
            try:
                btnCtx: ComponentContext = await wait_for_component(self.client, msg, timeout=60*60_000)

                if btnCtx.author_id != ctx.author_id:
                    await btnCtx.send("You can not interact with this game. Please start your own to do so!")
                    continue

                _btn, _gameId, _status, _index = btnCtx.custom_id.split("_")
                status = int(_status)
                index = int(_index)

                if gameEnded:
                    await btnCtx.send("This game has ended. Please start a new one!", hidden=True)
                    continue

                if status == 0:
                    cups[index] = 3
                    gameEnded = True
                    message = "💔 You have lost half of your bet"
                    em.title = message

                    new_comp = await self.rebuildComponents(cups, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    await self.client.addcoins(ctx.author_id, bet/2, "Lost only half bet in `/hidden_cups`\nReturning half back")

                    _em = discord.Embed(color=self.client.failure, description=message)
                    _em.set_footer(text="TN | Hidden Cups", icon_url=self.client.png)

                    await btnCtx.reply(embed=_em, hidden=True)
                    
                if status == 1:
                    cups[index] = 4
                    gameEnded = True
                    message = "💰 You have won 2x your bet!"
                    em.title = message

                    new_comp = await self.rebuildComponents(cups, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    if self.winnings[ctx.author_id]["total"] >= 1_000_000:
                        bet = bet
                    else:
                        self.winnings[ctx.author_id]["total"] += bet*2
                        if self.winnings[ctx.author_id]["total"] > 1_000_000:
                            difference = self.winnings[ctx.author_id]["total"] - 1_000_000
                            bet *= 2
                            bet -= difference
                        else:

                            bet *= 2

                    await self.client.addcoins(ctx.author_id, bet, "Won 2x bet in `/hidden_cups`")

                    _em = discord.Embed(color=self.client.failure, description=message)
                    _em.set_footer(text="TN | Hidden Cups", icon_url=self.client.png)

                    await btnCtx.reply(embed=_em, hidden=True)

                if status == 2:
                    cups[index] = 5
                    gameEnded = True
                    message = "☠️ You have lost all your bet..."
                    em.title = message

                    new_comp = await self.rebuildComponents(cups, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    _em = discord.Embed(color=self.client.failure, description=message)
                    _em.set_footer(text="TN | Hidden Cups", icon_url=self.client.png)

                    await btnCtx.reply(embed=_em, hidden=True)
    
            except asyncio.TimeoutError:
                em.title = "⏲️ Game ended due to inactivity"
                gameEnded = True
                await self.client.addcoins(ctx.author_id, bet, "`/hidden_cups` was cancelled")

                await msg.edit(embed=em, components=[], content=None)
                return

def setup(client):
    client.add_cog(HiddenCups(client))
