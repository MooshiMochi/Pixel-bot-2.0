import discord
import asyncio

from random import shuffle

from uuid import uuid4

from discord.ext import commands

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

from constants import const


class BuriedTreasure(commands.Cog):
    def __init__(self, client):
        self.client = client

    
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


    @cog_slash(name="buried_treasure", description="Bet some 💸 for a chance to gain 4x back", guild_ids=const.slash_guild_ids, options=[
        create_option(name="bet", description="The amount of 💸 you would like to bet", option_type=3, required=True)
    ])
    async def buried_treasure(self, ctx:SlashContext, bet:str=None):
        
        SQUARES = 25
        SUCCESS = 3

        changes = 2    

        bet = await self.client.parse_int(bet)

        failure_em = (
            discord.Embed(color=self.client.failure, description="")
            .set_footer(
                text="TN | Buried Treasure", 
                icon_url=self.client.png))

        if bet < 100:
            failure_em.description = "You need at least 100 💸"
            return await ctx.send(embed=failure_em, hidden=True)

        await self.check_user(ctx.author_id)
        
        auth_data = self.client.economydata[str(ctx.author_id)]

        if auth_data["wallet"] < bet:
            failure_em.description = "**You don't have enough 💸 in your wallet.\nWithdraw some from the bank using `/withdraw`.**"
            return await ctx.send(embed=failure_em, hidden=True)
        
        msg = await ctx.send("⌛ Your game is loading...")
        
        await self.client.addcoins(ctx.author_id, -bet, "Bet in `/buried_treasure`")

        attempts = 0
        gameEnded = False
        gameId = uuid4()

        buttonStatuses = list(map(lambda f: 1 if f < SUCCESS else 0, range(SQUARES)))

        shuffle(buttonStatuses)

        em = (
            discord.Embed(
                color=self.client.failure,
                description=f"💸 Your bet: **{int(bet):,} 💸**\n\n📜 Game Rules 📜\n\n- You can click on 3 spots in the sand using the buttons below.\n- 3 of these spots contain treasure.\n- If you find one of the spots with treasure, your bet is multiplied by 4!\n- Good luck and have fun!")
            .set_footer(text="TN | Buried Treasure", icon_url=self.client.png)
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

                    await self.client.addcoins(ctx.author_id, bet*4, "Won 4x bet in /buried_treasure")

                    new_comp = await self.rebuildComponents(buttonStatuses, gameId)
                    await btnCtx.edit_origin(embed=em, components=new_comp)

                    new_em = discord.Embed(color=self.client.failure, description=f"💰 Congrats! This part of the island included a treasre!\nYou won **{bet*4}** 💸!")

                    await btnCtx.send(embed=new_em, hidden=True)

            except asyncio.TimeoutError:
                em.title = "⏲️ Game ended due to inactivity"
                gameEnded = True
                await self.client.addcoins(ctx.author_id, bet, "`/buried_treasure` was cancelled")

                await msg.edit(embed=em, components=[], content=None)
                return

def setup(client):
    client.add_cog(BuriedTreasure(client))
