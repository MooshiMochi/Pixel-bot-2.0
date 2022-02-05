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
            self.client.user_cache[id] = ret.name
            return ret
        return f"~~{id}~~"

    @tasks.loop(minutes=1.0)
    async def update_leaderboards(self):

        with open("data/leaderboards.json", "w") as f:
            json.dump(self.client.lbs, f, indent=2)
    
    @update_leaderboards.before_loop
    async def before_update_leaderboards(self):
        await self.client.wait_until_ready()


    @cog_slash(name="leaderboard", description="Display the messages leaderboard", guild_ids=const.slash_guild_ids)
    async def leaderboard(self, ctx:SlashContext):
        
        await ctx.defer(hidden=False)

        if not self.client.lbs.get("chatlb", None):
            return await ctx.send("I have no leaderboard data yet. Please wait for someone to start talking.")

        ranked = sorted(self.client.lbs["chatlb"], key=lambda f: self.client.lbs["chatlb"][f]["total_xp"], reverse=True)

        embeds = []

        add_on = [y for y in range(9, len(self.client.lbs["chatlb"]), 10)] if len(self.client.lbs["chatlb"]) >= 10 else [len(self.client.lbs["chatlb"])-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.client.lbs["chatlb"])-1)
        
        em = discord.Embed(color=self.client.failure, title="Levels Leaderboard", description="")
        
        MyID = str(ctx.author_id)

        for x in range(len(self.client.lbs["chatlb"])):
            
            name = self.client.lbs["chatlb"][ranked[x]]["name"]
            level = self.client.lbs["chatlb"][ranked[x]]["level"]
            
            if x == 0:
                if ranked[x] == MyID:
                    em.description += f"**🏆. `(Me)` {name}** - Lvl {level}\n"
                else:
                    em.description += f"**🏆. {name}** - Lvl {level}\n"
            elif x == 1:
                if ranked[x] == MyID:
                    em.description += f"**🥈. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**🥈. {name}** - lvl {level}\n"
            elif x == 2:
                if ranked[x] == MyID:
                    em.description += f"**🥉. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**🥉. {name}** - lvl {level}\n"
            else:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**{x+1}. {name}** - lvl {level}\n"

            if x in add_on:
                em.set_footer(text=f"TN | Leveling System | Page {add_on.index(x)+1}/{len(add_on)}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=self.client.failure, title="Levels Leaderboard", description="")

        await paginator(embeds, ctx).run()


    @cog_slash(name="mm_lb", description="Display the leaderboard for Minecraft Madness Tournaments or Casual most winners.", guild_ids=const.slash_guild_ids, 
    options=[
        create_option(name="type", description="The game type (Casual or Tournament)", option_type=3, 
        choices=[
            create_choice(value="casual", name="Casual"),
            create_choice(value="torunament", name="Tournament")], required=False),
        create_option(name="member", description="The member to check mm stats for", option_type=6, required=False)])
    async def mm_lb(self, ctx:SlashContext, type:str=None, member:discord.Member=None):
        
        await ctx.defer(hidden=True)
        
        if type:
            embeds = await self.generate_lb(type, ctx.author.id)
            if embeds[0] == 1:
                return await paginator(embeds, ctx).run()
            else:
                return await ctx.send("The leaderboard is empty as of right now. Come back later!", hidden=True)
        elif not type and not member:
            return await ctx.send(embed=await self.generate_member_stats(ctx.author), hidden=True)
        
        elif not type and member:
            return await ctx.send(embed=await self.generate_member_stats(member), hidden=True)


    async def generate_member_stats(self, member:discord.Member=None):
        try:
            the_name = member.name
        except TypeError:
            the_name = "~~Unknown~~"

        em = discord.Embed(color=0x00F8EF, description="")
        em.set_author(name=f"{the_name}'s Minecraft Madness Stats:", icon_url=self.client.png)

        em.description = f"**Tournaments:** **`{self.client.lbs['mm_tournament'].get(str(member.id), 0)}`** wins.\n**Casual:** **`{self.client.lbs['mm_casual'].get(str(member.id), 0)}`** wins."
        return em

    async def generate_lb(self, leaderboard:str=None, author:int=None):
        em = discord.Embed(color=0x00F8EF, title=f"Minecraft Madness ({leaderboard.capitalize()}) Leaderboard")
        em.set_author(name="\u200b", icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))

        if leaderboard == "casual":
            ad = f"The leaderboard for the biggest 'Minecraft Madness' (casual) winners in Pixels Minecraft Lounge.\n\n"

            if not self.client.lbs["mm_casual"]:
                em.description = ad + f"`No players yet!`"
                return [0, em]

        else:
            ad = f"The leaderboard for the biggest 'Minecraft Madness' (tournaments) winners in Pixels Minecraft Lounge for month #{self.client.payouts['mm']['month']}. The top 10 biggest winners win cash prizes every month!\n\n*Wins only count for Minecraft Madness Tournaments\n\n1st of every month at 00:01/12 AM EST and all monthly tournament winners are reset*\n\n"

            if not self.client.lbs["mm_tournament"]:
                em.description = ad + f"`No players yet!`"
                return [0, em]

        em.description = ad

        game_type = "mm_"+leaderboard

        embeds = []

        ranked = sorted(self.client.lbs[game_type], key=lambda f: self.client.lbs[game_type][f], reverse=True)

        add_on = [y for y in range(9, len(self.client.lbs[game_type]), 10)] if len(self.client.lbs[game_type]) >= 10 else [len(self.client.lbs[game_type])-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.client.lbs[game_type])-1)

        MyID = str(author)

        for x in range(len(self.client.lbs[game_type])):
            
            name = await self.get_user(int(ranked[x]))
            wins = self.client.lbs[game_type][ranked[x]]
            
            if x == 0:
                if ranked[x] == MyID:
                    em.description += f"🏆 - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 500k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"🏆 - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 500k\n" if game_type == "tournament" else "\n"
            elif x == 1:
                if ranked[x] == MyID:
                    em.description += f"🥈 - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 400k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"🥈 - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 400k\n" if game_type == "tournament" else "\n"
            elif x == 2:
                if ranked[x] == MyID:
                    em.description += f"🥉 - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 300k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"🥉 - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 300k\n" if game_type == "tournament" else "\n"

            elif x == 3:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 200k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 200k\n" if game_type == "tournament" else "\n"
            elif x == 4:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 100k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 100k\n" if game_type == "tournament" else "\n"
            elif x == 5:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 80k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 80k\n" if game_type == "tournament" else "\n"
            elif x == 6:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 60k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 60k\n" if game_type == "tournament" else "\n"
            elif x == 7:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 40k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 40k\n" if game_type == "tournament" else "\n"
            elif x == 8:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 20k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 20k\n" if game_type == "tournament" else "\n"
            elif x == 9:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}.** - **`(Me)` {name}** - ({wins} wins)" + " - <:money:903467440829259796> 10k\n" if game_type == "tournament" else "\n"
                else:
                    em.description += f"**{x+1}.** - **{name}** - ({wins} wins)" + " - <:money:903467440829259796> 10k\n" if game_type == "tournament" else "\n"
            else:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}. - `(Me)` {name}** - ({wins} wins)\n"
                else:
                    em.description += f"**{x+1}. - {name}** - ({wins} wins)\n"

            if x in add_on:
                em.set_footer(text=f"TN | Minecraft Madness | Page {add_on.index(x)+1}/{len(add_on)}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=0x00F8EF, title=f"Minecraft Madness ({leaderboard.capitalize()}) Leaderboard", description="")
                em.set_author(name="\u200b", icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))

                em.description = ad
        return [1, embeds]

def setup(client):
    client.add_cog(LeaderboardCommands(client))