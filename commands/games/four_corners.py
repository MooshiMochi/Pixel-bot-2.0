from turtle import hideturtle
import discord
import asyncio

from random import shuffle

from discord.ext import commands

from datetime import datetime

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle, BucketType

from constants import const


class FourCorners(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cooldowns = {}

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
    async def rebuildComponents():        
        status = [0, 0, 0, 1]

        btns = [
            create_button(
                style=ButtonStyle.green,
                label="\u200b",
                custom_id=f"FourCornersBtn_{status[0]}_0"
            ),
            create_button(
                style=ButtonStyle.gray,
                label="\u200b",
                custom_id=f"FourCornersBtn_{status[1]}_1"
            ),
            create_button(
                style=ButtonStyle.blue,
                label="\u200b",
                custom_id=f"FourCornersBtn_{status[2]}_2"
            ),
            create_button(
                style=ButtonStyle.red,
                label="\u200b",
                custom_id=f"FourCornersBtn_{status[3]}_3"
            ),
        ]
        shuffle(btns)
        rows = [create_actionrow(*btns[:2]), create_actionrow(*btns[2:]), create_actionrow(*[
            create_button(
                style=ButtonStyle.green,
                label="Cash Out!",
                custom_id="FourCornersBtn_2_4"
            )
        ])]
        return rows


    @cog_slash(name="four_corners", description="Choose one of the correct buttons to double your bet.", guild_ids=const.slash_guild_ids, options=[
        create_option(name="bet", description="The amount of 💸 you would like to bet", option_type=3, required=True)
    ])
    async def four_corners(self, ctx:SlashContext, bet:str=None):

        if datetime.utcnow().timestamp() - self.cooldowns.get(ctx.author_id, 0) < 24*60*60:
            embed = discord.Embed(title="Woah, calm down.",
                                  description=f"This command is on cooldown.\nYou may try again in **{await self.client.sec_to_time(int((self.cooldowns.get(ctx.author_id, 0) + 24*60*60) - datetime.utcnow().timestamp()))}**",
                                  color=self.client.failure)
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text="TitanMC | Titan Network")
            try:
                return await ctx.send(embed=embed, hidden=True)
            except discord.HTTPException:
                return

        if "game" not in ctx.channel.name.lower():
            warn = discord.Embed(description="You can use this command in game channels only.", color=self.client.failure)
            warn.set_footer(text="TitanMC | Four Corners", icon_url=self.client.png)
            return await ctx.send(embed=warn, hidden=True)
        
        bet = await self.client.parse_int(bet)
        bet_copy = bet

        failure_em = (
            discord.Embed(color=self.client.failure, description="")
            .set_footer(
                text="TitanMC | Four Corners", 
                icon_url=self.client.png))

        if bet < 100:
            failure_em.description = "You need at least 100 💸"
            return await ctx.send(embed=failure_em, hidden=True)

        elif bet > 50_000:
            failure_em.description = "You cannot bet more than **50k 💸** at a time."
            return await ctx.send(embed=failure_em, hidden=True)

        await self.check_user(ctx.author_id)
        
        auth_data = self.client.economydata[str(ctx.author_id)]

        if auth_data["wallet"] < bet:
            failure_em.description = "**You don't have enough 💸 in your wallet.\nWithdraw some from the bank using `/withdraw`.**"
            return await ctx.send(embed=failure_em, hidden=True)

        self.cooldowns[ctx.author_id] = datetime.utcnow().timestamp()
        
        msg = await ctx.send("⌛ Your game is loading...")
        
        await self.client.addcoins(ctx.author_id, -bet, "Bet in `/four_corners`", where="wallet")

        allowCashOut = False

        em = discord.Embed(color=self.client.failure, description=f"💸 Your bet: **{int(bet):,}** 💸\n\n📜 Game Rules 📜\n\nHere are 4 buttons. 3 of the 4 buttons are good, one is bad.\nEach time you press one of the 3 good buttons, your bet will be doubled.\nYou can choose to 'Cash Out' anytime.\n\n**However**, if you press the incorrect button, you will lose your bet + half your **__NET WORTH__**.\nYou have one attempt. Good luck and have fun!\n\n*You can only play this game once every 24 hours*")
        em.set_footer(text="TitanMC | Four Corners", icon_url=self.client.png)
        em.set_author(name="🔳 Four Corners")

        components = await self.rebuildComponents()
        
        await msg.edit(embed=em, components=components, content=None)

        # multiplier = -0.00004*bet + 3.2
        multiplier = 1.9 * 0.99999 ** bet

        while 1:
            try:
                btnCtx: ComponentContext = await wait_for_component(self.client, msg, timeout=300)

                if btnCtx.author_id != ctx.author_id:
                    await btnCtx.send("You can not interact with this game. Please start your own to do so!", hidden=True)
                    continue

                _btn, _status, _index = btnCtx.custom_id.split("_")
                status = int(_status)

                if status == 1:
                    em.title = "❌ Pressed incorrect button"

                    total_worth = self.client.economydata[str(ctx.author_id)]["wallet"] + self.client.economydata[str(ctx.author_id)]["bank"]
                    
                    if total_worth != 0:
                        embed = discord.Embed(color=self.client.failure, description=f"**❌ You pressed the incorrect button.\nYou lost __{int(total_worth/2):,}__ 💸**")
                    else:
                        embed = discord.Embed(color=self.client.failure, description=f"**❌ You pressed the incorrect button.\nYou lost __absolutely no__ 💸** because you're already broke.")
                    embed.set_footer(text="TitanMC | Four Corners", icon_url=self.client.png)

                    self.client.economydata[str(ctx.author_id)]["bank"] += self.client.economydata[str(ctx.author_id)]["wallet"]
                    self.client.economydata[str(ctx.author_id)]["wallet"] = 0

                    await self.client.addcoins(ctx.author_id, -total_worth/2, "Clicked incorrect button in `/four_corners`.\nLost half net worth.")

                    await btnCtx.edit_origin(embed=em, components=[])
                    await ctx.send(embed=embed, hidden=True)
                    return
                
                elif status == 0:
                    bet_copy *= multiplier
                    if bet_copy >= 1_000_000:
                        bet_copy = 1_000_000

                        em.title = "💵 Max Winnings Reached"

                        _em = discord.Embed(color=self.client.failure, description=f"You reached the maximum winnings amount for this game.\nYou received **1,000,000 💸**")
                        _em.set_footer(text="TitanMC | Four Corners", icon_url=self.client.png)

                        await self.client.addcoins(ctx.author_id, int(bet_copy), "Max winnings reached in `/four_corners`", where="wallet")

                        await btnCtx.edit_origin(embed=em, components=[])
                        return await ctx.send(embed=_em, hidden=True)

                    await ctx.send(f"Your money got multiplied by {multiplier:.2f} again!\nYou have **{int(bet_copy):,} 💸** in winnings so far.", hidden=True)
                    allowCashOut = True

                elif status == 2:

                    if not allowCashOut:
                        await btnCtx.send("You cannot Cash Out right now. Chose one of the buttons first!", hidden=True)
                        continue

                    em.title = "💵 Cashed out!"

                    await ctx.send(f"You won a total of **{int(bet_copy):,} 💸**", hidden=True)
                    await btnCtx.edit_origin(embed=em, components=[])

                    await self.client.addcoins(ctx.author_id, bet_copy, "Cashed out in `/four_corners`", where="wallet")
                    return

                new_rows = await self.rebuildComponents()
                await btnCtx.edit_origin(components=new_rows)

            except asyncio.TimeoutError:
                em.title = "⏲️ Game ended due to inactivity"
                await self.client.addcoins(ctx.author_id, bet, "`/four_corners` was cancelled", where="wallet")
                self.cooldowns.pop(ctx.author_id, None)
                await msg.edit(embed=em, components=[], content=None)
                return

def setup(client):
    client.add_cog(FourCorners(client))