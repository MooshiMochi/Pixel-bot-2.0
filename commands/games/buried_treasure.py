import discord
import asyncio

from random import shuffle

from uuid import uuid4

from discord.ext import commands

from datetime import datetime

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

from constants import const


class BuriedTreasure(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.winnings = {}

    
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
    
    @staticmethod
    async def rebuildComponents(buttonStatuses:list=[], gameId:str=None):
        buttons = []
        chunk = []

        for index, status in enumerate(buttonStatuses):

            emoji = "🏝️" if (status == 0 or status == 1) else "💰" if status == 2 else "🏝️"

            style = ButtonStyle.grey if (status == 0 or status == 1) else ButtonStyle.green if status == 2 else ButtonStyle.red

            chunk.append(
                create_button(
                    style=style,
                    emoji=emoji,
                    custom_id=f"BuriedTreasureBtn_{gameId}_{status}_{index}"
                )
            )

            if (index+1) % 5 == 0:
                buttons.append(chunk)
                chunk = []

        actions = [create_actionrow(*x) for x in buttons] 

        return actions


    @cog_slash(name="buried_treasure", description="Bet some 💸 for a chance to gain 6x back", guild_ids=const.slash_guild_ids, options=[
        create_option(name="bet", description="The amount of 💸 you would like to bet", option_type=3, required=True)
    ])
    async def buried_treasure(self, ctx:SlashContext, bet:str=None):

        if "game" not in ctx.channel.name.lower():
            warn = discord.Embed(description="You can use this command in game channels only.", color=self.client.failure)
            warn.set_footer(text="TitanMC | Buried Treasure", icon_url=self.client.png)
            return await ctx.send(embed=warn, hidden=True)
        
        SQUARES = 25
        SUCCESS = 3

        changes = 2    

        bet = await self.client.parse_int(bet)

        failure_em = (
            discord.Embed(color=self.client.failure, description="")
            .set_footer(
                text="TitanMC | Buried Treasure", 
                icon_url=self.client.png))

        if bet < 100:
            failure_em.description = "You need at least 100 💸"
            return await ctx.send(embed=failure_em, hidden=True)

        await self.check_user(ctx.author_id)
        
        auth_data = self.client.economydata[str(ctx.author_id)]

        if auth_data["wallet"] < bet:
            failure_em.description = "**You don't have enough 💸 in your wallet.\nWithdraw some from the bank using `/withdraw`.**"
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
            __em.set_footer(text=f"TitanMC | Buried Treasure", icon_url=self.client.png)

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

                        if e["wallet"] < self.client.play_price + bet:
                            err = discord.Embed(color=self.client.failure, description="You are too poor to afford this.\nWithdraw some more money from your bank and try again.")
                            err.set_footer(text="TitanMC | Buried Treasure", icon_url=self.client.png)
                            await ctx.send(embed=err, hidden=True)
                            raise asyncio.TimeoutError
                        else:
                            await self.client.addcoins(ctx.author_id, -self.client.play_price, "Purchased 1 play ticket for 'Buried Treasure'", where="wallet")
                        
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
        
        await self.client.addcoins(ctx.author_id, -bet, "Bet in `/buried_treasure`", where="wallet")

        attempts = 0
        gameEnded = False
        gameId = uuid4()

        buttonStatuses = list(map(lambda f: 1 if f < SUCCESS else 0, range(SQUARES)))

        shuffle(buttonStatuses)

        em = (
            discord.Embed(
                color=self.client.failure,
                description=f"💸 Your bet: **{int(bet):,} 💸**\n\n📜 Game Rules 📜\n\n- You can click on 3 spots in the sand using the buttons below.\n- 3 of these spots contain treasure.\n- If you find one of the spots with treasure, your bet is multiplied by 6!\n- Good luck and have fun!\n\n*You only have 5 free attempts to play any of the games, after which you will be charged a fee.*")
            .set_footer(text="TitanMC | Buried Treasure", icon_url=self.client.png)
            .set_author(name="🏝️ Buried Treasure")
        )

        components = await self.rebuildComponents(buttonStatuses, gameId)

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

                if status in (2, 3):
                    await btnCtx.send("You have already discovered this part of the island!", hidden=True)

                if status == 0:
                    attempts += 1
                    buttonStatuses[index] = 3
                    if attempts == SUCCESS:
                        em.title="😢 Game lost..."
                        gameEnded = True
            
                    new_comp = await self.rebuildComponents(buttonStatuses, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    _em = discord.Embed(color=self.client.failure, description=f"🏝️ Unfortunately this part of this island did not include a treasure!")

                    _em.description += "\n🤞 The game is over. Good luck next time!" if gameEnded else f"\nYou have **{SUCCESS - attempts}** more attempts to find the treasure!"

                    await btnCtx.reply(embed=_em, hidden=True)

                if status == 1:
                    buttonStatuses[index] = 2
                    em.title = "💰 Game won!"
                    gameEnded = True

                    if self.winnings[ctx.author_id]["total"] >= 1_000_000:
                        bet = bet
                    else:
                        bet *= 6
                        self.winnings[ctx.author_id]["total"] += bet
                        if self.winnings[ctx.author_id]["total"] > 1_000_000:
                            difference = self.winnings[ctx.author_id]["total"] - 1_000_000
                            bet -= difference
                        

                    await self.client.addcoins(ctx.author_id, bet, "Won 6x bet in /buried_treasure", where="wallet")

                    new_comp = await self.rebuildComponents(buttonStatuses, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    new_em = discord.Embed(color=self.client.failure, description=f"💰 Congrats! This part of the island included a treasre!\nYou won **{bet}** 💸!")

                    await btnCtx.send(embed=new_em, hidden=True)
                    if bet == 0:
                        await ctx.send("Since you already reached your maximum winnings for the day, you will not be getting any rewards...")

            except asyncio.TimeoutError:
                em.title = "⏲️ Game ended due to inactivity"
                gameEnded = True
                await self.client.addcoins(ctx.author_id, bet, "`/buried_treasure` was cancelled", where="wallet")

                await msg.edit(embed=em, components=[], content=None)
                return

def setup(client):
    client.add_cog(BuriedTreasure(client))
