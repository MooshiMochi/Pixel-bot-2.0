import json
import discord

from discord.ext import commands, tasks

from discord_slash.cog_ext import cog_slash
from discord_slash import SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice

from utils.paginator import Paginator as paginator

from constants import const


class LeaderboardCommands(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.update_leaderboards.start()

    async def get_user(self, id:int=None) -> str:
        await self.client.wait_until_ready()
        id = int(id)

        ret = self.client.user_cache.get(id, None)
        ret = self.client.get_guild(const.guild_id).get_member(id) if not ret else ret

        if ret:
            if isinstance(ret, discord.Member):
                self.client.user_cache[id] = ret.name
            return ret
        return f"~~{id}~~"

    @tasks.loop(minutes=1.0)
    async def update_leaderboards(self):

        with open("data/leaderboards.json", "w") as f:
            json.dump(self.client.lbs, f, indent=2)

        with open("data/verified_players.json", "w") as f:
            json.dump(self.client.players, f, indent=2)
    
    @update_leaderboards.before_loop
    async def before_update_leaderboards(self):
        await self.client.wait_until_ready()


    @cog_slash(name="lb", description="Display the leaderboard for various games and most winners within them", guild_ids=const.slash_guild_ids, 
    options=[
        create_option(name="game_type", description="The game type", option_type=3, 
        choices=[
            create_choice(value="mm_casual", name="Minecraft Madness Casual"),
            create_choice(value="mm_tournament", name="Minecraft Madness Tournament"),
            create_choice(value="riddles", name="Riddles"),
            create_choice(value="chatlb", name="Level System"),
            create_choice(value="msgs", name="Messages")], required=True),
        create_option(name="member", description="The member to check mm stats for", option_type=6, required=False)])
    async def lb(self, ctx:SlashContext, game_type:str=None, member:discord.Member=None):
        
        if not member:
            await ctx.defer(hidden=True)

            embeds = await self.generate_lb(game_type, ctx.author.id, "Minecraft Madness" if game_type.startswith("mm_") else "Riddles" if game_type == "riddles" else "Levels" if game_type == "chatlb" else "Messages")
            if embeds[0] == 1:
                return await paginator(embeds[1], ctx).run()
            else:
                return await ctx.send("The leaderboard is empty as of right now. Come back later!", hidden=True)
        elif member:
            if game_type in ["mm_casual", "mm_tournament"]:
                await ctx.defer(hidden=True)
                return await ctx.send(embed=await self.generate_member_stats(ctx.author), hidden=True)

            elif game_type == "riddles":
                await ctx.defer(hidden=True)
                em = discord.Embed(color=self.client.failure)
                em.set_author(name=f"{member.name}'s Riddles Stats:", icon_url=self.client.png)
                em.description = f"**Riddles Guessed:** **`{self.client.lbs[game_type].get(str(member.id), 0)}`**."
                return await ctx.send(embed=em, hidden=True)

            elif game_type == "chatlb":
                await ctx.invoke(self.client.slash.commands["level"], member=member)
            
            elif game_type == "msgs":
                await ctx.defer(hidden=True)
                em = discord.Embed(color=self.client.failure)
                em.set_author(name=f"{member.name}'s Messages Stats:", icon_url=self.client.png)
                em.description = f"**Total Messages:** **`{self.client.lbs[game_type].get(str(member.id), 0)}`**."
                return await ctx.send(embed=em, hidden=True)


    async def generate_member_stats(self, member:discord.Member=None):
        try:
            the_name = member.name
        except TypeError:
            the_name = "~~Unknown~~"

        em = discord.Embed(color=self.client.failure, description="")
        em.set_author(name=f"{the_name}'s Minecraft Madness Stats:", icon_url=self.client.png)

        em.description = f"**Tournaments:** **`{self.client.lbs['mm_tournament'].get(str(member.id), 0)}`** wins.\n**Casual:** **`{self.client.lbs['mm_casual'].get(str(member.id), 0)}`** wins."
        return em

    async def generate_lb(self, leaderboard:str=None, author:int=None, footer:str=None):

        filler = f" ({leaderboard.replace('mm_', '').capitalize()})" if leaderboard not in ("chatlb", "msgs") else ""

        em = discord.Embed(color=self.client.failure, title=f"{footer}{filler} Leaderboard")
        em.set_author(name="\u200b", icon_url=self.client.png)
        em.set_footer(text=f"TN | {footer}", icon_url=self.client.png)

        if leaderboard == "mm_casual":
            ad = f"The leaderboard for the biggest 'Minecraft Madness' (casual) winners in Titan Network Lounge.\n\n"

        elif leaderboard == "mm_tournament":
            ad = f"The leaderboard for the biggest 'Minecraft Madness' (tournaments) winners in Titan Network Lounge for month #{self.client.payouts['mm']['month']}. The top 10 biggest winners win cash prizes every month!\n\n*Wins only count for Minecraft Madness Tournaments\n\n1st of every month at 00:01/12 AM EST and all monthly tournament winners are reset*\n\n"

        elif leaderboard == "msgs":
            ad = f"The leaderboard for the biggest chatters in Titan Network Lounge for week #{self.client.payouts['msgs']['month']}.\nThe top 10 chatters win cash prizes in the games rooms every week!\n*Messages only count in lounge channels*\n\n*Weeks end Monday 00:01/12 AM EST and all weekly messages are reset*\n\n"

        else:
            ad = ""
            
        if not self.client.lbs[leaderboard]:
            em.description = f"`No players yet!`"
            return [0, em]

        em.description = ad

        game_type = leaderboard

        embeds = []

        if game_type == "chatlb":
            ranked = sorted(self.client.lbs[game_type], key=lambda f: self.client.lbs[game_type][f]["total_xp"], reverse=True)
        else:
            ranked = sorted(self.client.lbs[game_type], key=lambda f: self.client.lbs[game_type][f], reverse=True)


        add_on = [y for y in range(9, len(self.client.lbs[game_type]), 10)] if len(self.client.lbs[game_type]) >= 10 else [len(self.client.lbs[game_type])-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.client.lbs[game_type])-1)

        MyID = str(author)

        check_tup = ("mm_tournament", "msgs")

        for x in range(len(self.client.lbs[game_type])):
            
            name = await self.get_user(int(ranked[x])) if game_type != "chatlb" else self.client.lbs["chatlb"][ranked[x]]["name"]
            wins = self.client.lbs[game_type][ranked[x]] if game_type != "chatlb" else self.client.lbs["chatlb"][ranked[x]]["level"]

            brckt = f"lvl {wins}" if game_type == "chatlb" else f"{wins} wins" if game_type in ("mm_tournament", "mm_casual") else f"{wins} messages" if game_type == "msgs" else f"{wins}"

            if x == 0:
                if ranked[x] == MyID:
                    em.description += f"🏆 - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 500k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"🏆 - **{name}** - ({brckt})"
                    em.description += " - 💸 500k\n" if game_type in check_tup else "\n"
            elif x == 1:
                if ranked[x] == MyID:
                    em.description += f"🥈 - **`(Me)` {name}** - ({brckt})"
                    em.description += f" - 💸 400k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"🥈 - **{name}** - ({brckt})"
                    em.description += f" - 💸 400k\n" if game_type in check_tup else "\n"
            elif x == 2:
                if ranked[x] == MyID:
                    em.description += f"🥉 - **`(Me)` {name}** - ({brckt})" 
                    em.description += " - 💸 300k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"🥉 - **{name}** - ({brckt})"
                    em.description += " - 💸 300k\n" if game_type in check_tup else "\n"

            elif x == 3:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 200k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 200k\n" if game_type in check_tup else "\n"
            elif x == 4:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 100k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 100k\n" if game_type in check_tup else "\n"
            elif x == 5:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 80k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 80k\n" if game_type in check_tup else "\n"
            elif x == 6:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 60k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 60k\n" if game_type in check_tup else "\n"
            elif x == 7:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 40k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 40k\n" if game_type in check_tup else "\n"
            elif x == 8:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 20k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 20k\n" if game_type in check_tup else "\n"
            elif x == 9:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({brckt})"
                    em.description += " - 💸 10k\n" if game_type in check_tup else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({brckt})"
                    em.description += " - 💸 10k\n" if game_type in check_tup else "\n"
            else:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}. - `(Me)` {name}** - ({brckt})\n"
                else:
                    em.description += f"**{x+1}. - {name}** - ({brckt})\n"

            if x in add_on:
                em.set_footer(text=f"TN | {footer} | Page {add_on.index(x)+1}/{len(add_on)}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=self.client.failure, title=f"{footer}{filler} Leaderboard", description="")
                em.set_author(name="\u200b", icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
                em.set_footer(text=f"TN | {footer}", icon_url=self.client.png)

                em.description = ad
        return [1, embeds]

def setup(client):
    client.add_cog(LeaderboardCommands(client))
