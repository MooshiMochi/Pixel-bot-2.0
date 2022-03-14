import discord

from uuid import uuid4

from random import randint

from asyncio import TimeoutError, sleep

from discord import AllowedMentions
from discord.ext import commands

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component

from constants import const

class CoinFlip(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.btns_accept_n_deny = create_actionrow(*[
            create_button(
                custom_id="accept_" + str(uuid4()),
                style=ButtonStyle.green,
                label="Accept",
                emoji="⚔️"),
            
            create_button(
                custom_id="deny_" + str(uuid4()),
                style=ButtonStyle.red,
                label="Deny",
                emoji="⛔")
        ])

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
    
    async def get_bet_amount(self, ctx: SlashContext, accept_member: discord.Member) -> float:
        
        while 1:
            try:
                msg = await self.client.wait_for("message", check=lambda msg_obj: msg_obj.author.id == accept_member.id, timeout=15)

                try:
                    clean_content = msg.content.replace(" ", "").replace(",", "").lower()

                    return await self.client.parse_int(clean_content), msg

                except (ValueError, TypeError):
                    await ctx.send("Please enter a number. Example: `100000 / 10k / 953,312`", delete_after=10)
            except TimeoutError:
                return False, None


    @cog_slash(name="coin_flip_duel", description="Challenge someone to a coin flip duel", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The person to challenge", option_type=6, required=True),
        create_option(name="bet_amount", description="Amount of 💸 you will put on the line in this duel", option_type=3, required=True)
    ])
    async def coin_flip_duel(self, ctx: SlashContext, member:discord.Member=None, bet_amount:str=None):

        if "game" not in ctx.channel.name.lower():
            warn = discord.Embed(description="You can use this command in game channels only.", color=self.client.failure)
            warn.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
            return await ctx.send(embed=warn, hidden=True)

        if isinstance(member, int):
            return await ctx.send("That person is no longer in this server. Try duel someone else!", hidden=True)
        
        if member.id == ctx.author.id:
            return await ctx.send("You cannot challenge yourself.", hidden=True)

        if member.id == self.client.user.id:
            return await ctx.send("I am yet to be rich enough to afford this...", hidden=True)
        
        if member.bot:
            return await ctx.send("Bots are the most broke out of all server members. They own NOTHING!", hidden=True)

        p1_bet = int(await self.client.parse_int(bet_amount))

        if p1_bet <= 0:
            return await ctx.send("Minimum you can bet on a game is 100 💸", hidden=True)

        author_wallet = (await self.check_user(ctx.author_id))["wallet"]

        if author_wallet - p1_bet < 0:
            return await ctx.send("You do not have that much 💸 in your wallet.", hidden=True)

        p2_wallet = (await self.check_user(member.id))["wallet"]

        self.client.economydata[str(ctx.author_id)]["wallet"] -= p1_bet

        prefix_int = await self.client.round_int(p1_bet)

        inv = discord.Embed(color=self.client.failure, description=f"**⚔️ <@!{ctx.author_id}> has invited you to a coin flip duel!** ⚔️\n\n*{ctx.author.name} bet {prefix_int} 💸*\n\n`{member}, you have 30 seconds to decide!`")
        inv.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
        
        msg_duel = await ctx.send(content=member.mention, embed=inv, components=[self.btns_accept_n_deny])

        duelCtx = await self.client.get_context(msg_duel)

        accepted_msg = None

        while 1:
            try:
                btnCtx: ComponentContext = await wait_for_component(self.client, msg_duel, timeout=30)

                if btnCtx.author_id != member.id:
                    await btnCtx.send("You cannot interact with these buttons.", hidden=True)
                    continue

                elif btnCtx.custom_id.startswith("accept"):
                    accepted_msg = await duelCtx.send(f"\u200b\n{member.mention} has accepted the duel!")
                    await btnCtx.send(f"How much 💸 would you like to bet? (Minimum bet is {p1_bet:,})", hidden=True)
                    break

                elif btnCtx.custom_id.startswith("deny"):
                    await btnCtx.send(f"{member.mention} has declined the duel request!")

                    try:
                        await msg_duel.delete()
                    except (discord.HTTPException, discord.NotFound):
                        pass

                    self.client.economydata[str(ctx.author_id)]["wallet"] += p1_bet

                    return

            except TimeoutError:
                self.client.economydata[str(ctx.author_id)]["wallet"] += p1_bet
                await ctx.send(f"{member.mention} did not respond to the duel request.", allowed_mentions=AllowedMentions(users=False))
                try:
                    await msg_duel.delete()
                except (discord.HTTPException, discord.Forbidden, discord.NotFound):
                    return
                return

        p2_bet = 0
        while 1:
            p2_bet, bet_entry_msg = await self.get_bet_amount(duelCtx, member)
            if p2_bet is False:
                cancelled = discord.Embed(color=self.client.failure, description=f"**⚔️ | Duel Cancelled**")
                cancelled.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
                await msg_duel.edit(embed=cancelled, components=[])

                self.client.economydata[str(ctx.author_id)]["wallet"] += p1_bet

                await sleep(5)
                try:
                    await msg_duel.delete()
                except (discord.HTTPException, discord.Forbidden, discord.NotFound):
                    return
                return

            elif p2_bet < p1_bet:
                await duelCtx.send(f"Minimum 💸 you can bet is {p1_bet:,}.", delete_after=5)
                continue
            elif p2_wallet - p2_bet < 0:
                await duelCtx.send(f"You do not have that much 💸 to bet.", delete_after=5)
                continue
            else:
                await bet_entry_msg.add_reaction("✅")
                break
        
        self.client.economydata[str(member.id)]["wallet"] -= p2_bet

        prefix_int2 = await self.client.round_int(p2_bet)

        confirm = discord.Embed(color=self.client.failure, description=f"**⚔️ Duel Starting** ⚔️\n\n*{ctx.author.name} bet {prefix_int} 💸*\n*{member.name} bet {prefix_int2}💸*")
        confirm.set_footer(text="TN | Coin Flip", icon_url=self.client.png)

        try:
            
            await duelCtx.channel.delete_messages([msg_duel, accepted_msg])

            msg_duel = await duelCtx.send(embed=confirm)
        except (discord.HTTPException, discord.Forbidden, discord.NotFound):
            print("A fucking error got in the way...")
            return await ctx.send("Oh no... It seems the game has been interrupted.")

        total_winnings = p1_bet + p2_bet

        pick_ar = [
            create_actionrow(*[
                create_button(
                    style=ButtonStyle.green,
                    label="Heads",
                    emoji="🪙",
                    custom_id=f"heads_{uuid4()}"
                ),
                create_button(
                    style=ButtonStyle.green,
                    label="Tails",
                    emoji="🪙",
                    custom_id=f"tails_{uuid4()}"
                )
            ])
        ]

        choice = discord.Embed(description=f"**{member.mention}, pick a side!**", color=self.client.failure)
        choice.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
        
        await sleep(3)

        try:
            await msg_duel.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass
        
        choice_msg = await ctx.send(embed=choice, components=pick_ar)

        mem_choice = 1 # Heads

        while 1:
            try:
                btnCtx: ComponentContext = await wait_for_component(self.client, choice_msg, timeout=30)

                if btnCtx.author_id != member.id:
                    await btnCtx.send("You cannot interact with these buttons.", hidden=True)
                    continue

                elif btnCtx.custom_id.startswith("heads"):
                    em = discord.Embed(color=self.client.failure, description=f"**{member.mention} chose __HEADS__.**\n\n*{ctx.author.mention} gets __TAILS__.*")
                    em.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
                    await btnCtx.edit_origin(embed=em, components=[])
                    break

                elif btnCtx.custom_id.startswith("tails"):
                    em = discord.Embed(color=self.client.failure, description=f"**{member.mention} chose __TAILS__.**\n\n*{ctx.author.mention} gets __HEADS__.*")
                    em.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
                    await btnCtx.edit_origin(embed=em, components=[])
                    mem_choice = 2 # Tails
                    break

            except TimeoutError:
                self.client.economydata[str(ctx.author_id)]["wallet"] += p1_bet
                self.client.economydata[str(member.id)]["wallet"] += p2_bet

                return await duelCtx.send(f"{member.mention} could not make a decision.")

        await sleep(3)

        result = randint(1, 2)

        winner = None

        if result == 1: # heads
            if mem_choice == 1:
                winner = member
            else:
                winner = ctx.author
            
        else:
            if mem_choice == 2:
                winner = member
            else:
                winner = ctx.author

        spinning = discord.Embed(description="**Spinning the coin!**", color=self.client.failure)
        spinning.set_image(url="https://media1.giphy.com/media/6jqfXikz9yzhS/giphy.gif")
        spinning.set_footer(text="TN | Coin Flip", icon_url=self.client.png)
        
        await choice_msg.edit(embed=spinning)

        await sleep(5)

        win_em = discord.Embed(color=self.client.failure, description=f"**🎉 Congratulations, {winner.mention}!\n\nYou won {await self.client.round_int(total_winnings)} 💸**")
        win_em.set_footer(text="TN | Coin Flip", icon_url=self.client.png)

        await choice_msg.edit(embed=win_em)

        await self.client.addcoins(winner.id, total_winnings, f"Won in a coin flip duel against {winner.name}#{winner.discriminator}", where="wallet")

        return

def setup(client):
    client.add_cog(CoinFlip(client))
