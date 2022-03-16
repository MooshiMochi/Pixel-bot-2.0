import json
import random
import asyncio
import discord

from datetime import datetime

from discord.ext import commands, tasks
from discord.mentions import AllowedMentions
from discord.ext.commands import MemberConverter

from utils.paginator import Paginator

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.model import ButtonStyle
from discord_slash.utils import manage_components
from discord_slash.utils.manage_commands import create_option, create_choice

from constants import const

mconv = MemberConverter()


class McMadness(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.client.user_cache = {}

        self.unbelievaboat_api_enabled = True

        with open("data/games/mm_config.json", "r") as f:
            self.config = json.load(f)
            if "active" not in self.config.keys():
                self.config["active"] = False
            if "mm_channel_id" not in self.config.keys():
                self.config["mm_channel_id"] = None
            if "tournament_id" not in self.config.keys():
                self.config["tournament_id"] = None
            if "ping_role_id" not in self.config.keys():
                self.config["ping_role_id"] = "\u200b"

        self.mm_channel_id = self.config.get("mm_channel_id", None)
        self.tournament_id = self.config.get("tournament_id", None)
        self.ping_role_str = self.config.get("ping_role_id", "\u200b")

        if self.ping_role_str:
            self.ping_role_str = "<@&"+str(self.ping_role_str)+">"

        self.event_channel = None
        self.mm_channel = None
        self.tournament_channel = None
        
        self.is_tournament = False
        
        self.prize_pool = 0
        
        self.game_explanation = None

        with open("data/games/quiz_questions.json", "r", encoding="utf8") as f:
            self.quiz_data = json.load(f)

        self.participants = {}
        self.members_ready = False
        self.game_cache = {"message": None, "answer": None, "easy": 0, "normal": 0, "hard": 0, "embed": None, "total": 0}
        self.correct_answer = "answer_not_yet_found"
        self.used_questions = []
        self.question_start_ts = 0
        self.users_guessed = []
        self.correct_option = "NOT_READY"
        self.is_event_ongoing = False
        self.give_10k_to_winner = False
        self.all_game_participants = {}
        self.eliminated = []

        self.get_ready.start()

    async def clear_variables(self):
        self.game_cache = {"message": None, "answer": None, "easy": 0, "normal": 0, "hard": 0, "total": 0}
        self.users_guessed = []
        self.members_ready = False
        self.question_start_ts = 0
        self.used_questions = []
        self.correct_answer = "answer_not_yet_found"
        self.participants = {}
        self.correct_option = "NOT_READY"
        self.prize_pool = 0
        self.give_10k_to_winner = False
        self.is_tournament = False
        self.is_event_ongoing = False
        self.eliminated = []
        self.all_game_participants = {}


    @tasks.loop(count=1)
    async def get_ready(self):
        
        self.event_channel = self.client.get_channel(self.mm_channel_id)
        self.mm_channel = self.client.get_channel(self.mm_channel_id)
        self.tournament_channel = self.client.get_channel(self.tournament_id)
        self.game_explanation = (discord.Embed(color=self.client.failure, title="Welcome to 'Minecraft Madness'!",
        description="This is a 'Minecraft Trivia Quiz' where people compete against\neach other to win the top prize (if there is one).\n\n"
        "You will be asked a series of multiple choice questions with increasing difficulty. You have to answer them by pressing the correct button.\n"
        "\nYou only get one chance per game. Good luck!").set_thumbnail(url=self.client.png))
        
        self.tournamet.start()

    @get_ready.before_loop
    async def before_get_ready(self):
        await self.client.wait_until_ready()


    async def get_user(self, id:int=None) -> str:
        await self.client.wait_until_ready()
        id = int(id)

        ret = self.client.user_cache.get(id, None)
        ret = self.client.get_guild(const.guild_id).get_member(id) if not ret else ret

        if ret:
            self.client.user_cache[id] = ret.name
            return ret
        return f"~~{id}~~"
    
    async def update_tournament_lb(self, id:int=None):

        if str(id) not in self.client.lbs["mm_tournament"].keys():
            self.client.lbs["mm_tournament"][id] = 1
        else:
            self.client.lbs["mm_tournament"][id] += 1

    async def update_casual_lb(self, id:int=None):
        id = str(id)

        if str(id) not in self.client.lbs["mm_casual"].keys():
            self.client.lbs["mm_casual"][id] = 1
        else:
            self.client.lbs["mm_casual"][id] += 1

    async def join_event(self, channel):
        start_time = datetime.utcnow().timestamp() + 60

        em = discord.Embed(color=self.client.failure, title="Minecraft Madness Event!", 
        description=f"*The event will begin <t:{int(start_time)}:R>*\n")

        em.add_field(name="Participants:", value="`No participants yet!`")

        join_button = [
            manage_components.create_button(
                style=ButtonStyle.green,
                label="Enter",
                custom_id="i_joined"
            )]
        
        action_row = [manage_components.create_actionrow(*join_button)]

        msg = await channel.send(embed=em, components=action_row)
        self.game_cache["embed"] = msg.embeds[0]

        while 1:
            if start_time - (datetime.utcnow().timestamp()) >= 0:
                await asyncio.sleep(start_time - (datetime.utcnow().timestamp()))
                break

        no_more_joins = [manage_components.create_button(
            style=ButtonStyle.danger,
            label="Event Started",
            custom_id="event_started",
            disabled=True
        )]
        action_row = [manage_components.create_actionrow(*no_more_joins)]
        
        if self.give_10k_to_winner:
            self.game_cache["embed"].description += "\n\nThe prize for the winner will be 💸 **10,000**"
        elif self.is_tournament:
            self.game_cache["embed"].description += f"\n\nThe prize for the winner will be 💸 **{len(self.participants.keys())*10000:,}**"

        await msg.edit(embed=self.game_cache["embed"], components=action_row)

        self.members_ready = True


    async def main_event_func(self):
        before_start = True

        while 1:
            if self.game_cache["total"] >= 116:

                templi = enumerate(sorted([tuple(x,) for x in self.participants.items()], key=lambda pts: pts[1], reverse=True))
                
                result = "\n".join([f'**{pos[0]}.** <@!{pos[1][0]}> ({pos[1][1]})' for pos in templi])

                em = discord.Embed(color=self.client.failure, title="GAME OVER!",
                description="It looks like you already answered all the questions that I had... damn!\nHere's the Leaderboard:\n"+result)
                
                await self.clear_variables()
                return await self.event_channel.send(embed=em)

            if before_start:
                before_start = False
                if len(self.participants) <= 1:
                    dont_start = discord.Embed(color=self.client.failure)
                    if len(self.participants) == 1:
                        member = await self.get_user(list(self.participants.keys())[0])
                        dont_start.set_author(name=f"Looks like the event is cancelled for today!\nOnly {member} joined :(",
                        icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
                        await self.clear_variables()
                        return await self.event_channel.send(embed=dont_start)
                    
                    elif len(self.participants) != 1:
                        dont_start.set_author(name=f"Looks like the event is cancelled for today!\nNo one joined :(",
                        icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
                        await self.clear_variables()
                        return await self.event_channel.send(embed=dont_start)

            main_em, ar, sleep_time = await self.prepare_question()

            msg = await self.event_channel.send(embed=main_em, components=ar)
            
            self.question_start_ts = datetime.utcnow().timestamp()
            
            stop_ts = datetime.utcnow().timestamp() + sleep_time[0] + sleep_time[1]
            sent_notif = False

            reminder = discord.Embed(color=self.client.failure).set_author(name=f"{sleep_time[1]} SECONDS LEFT TO GUESS", icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))

            while datetime.utcnow().timestamp() < stop_ts:

                if len(self.participants.keys()) == (len(self.users_guessed) + len(self.eliminated)):
                    break

                elif stop_ts - datetime.utcnow().timestamp() <= sleep_time[1]:
                    if not sent_notif:
                        await self.event_channel.send(embed=reminder, delete_after=sleep_time[1])
                        sent_notif = True

                await asyncio.sleep(1)
            
            await msg.delete()

            disqualified_users = []
            disc_text = "**The following members were disqualified**\n\n"
            disqualified = ""

            for id, pts in self.participants.copy().items():
                if id not in self.users_guessed:
                    del self.participants[id]
                    disqualified_users.append((id, pts))
                
                if (id not in self.eliminated) and (id not in self.users_guessed):
                    try:
                        del self.participants[id]
                    except KeyError:
                        pass
                    disqualified += f"<@!{id}> with **{pts}** points.\n"
            
            disqualified = disqualified[-(250 - len(disc_text)):]

            disc_em = discord.Embed(color=self.client.failure, description=disc_text + disqualified)
            if disqualified:
                await self.event_channel.send(embed=disc_em, delete_after=10)
            
            if not self.participants and disqualified_users:
                winner_id, winner_points = sorted(disqualified_users, key=lambda r: r[1], reverse=True)[0]

                text = f"<@!{winner_id}>, You are the last player standing with **{winner_points}** points!"
                if self.is_tournament:
                    await self.update_tournament_lb(winner_id) 
                    text += f"\n\nAs the sole survivor, you will receive 💸 **{self.prize_pool:,}**!"
                    if self.unbelievaboat_api_enabled:
                        await self.client.addcoins(winner_id, self.prize_pool, "Sole surviver of Minecraft Madness Tournament")
                else:
                    await self.update_casual_lb(winner_id) 
                    if self.give_10k_to_winner:
                        text += f"\n\nAs the sole survivor, you will receive 💸 **10,000**!"

                        if self.unbelievaboat_api_enabled:
                            await self.client.addcoins(winner_id, 10000, "Won in a Minecraft Madness game with 5+ participants")
                    
                win_em = discord.Embed(title="Game Over!", description=text, color=self.client.failure)
                win_em.set_thumbnail(url=self.client.user.avatar_url_as(static_format="png", size=2048))

                await self.clear_variables()
                await self.event_channel.send(embed=win_em)
                await self.event_channel.send("Check the win leaderboard with `/lb`")
                return

            elif len(self.participants) == 1:
                winner_id, winner_points = list(self.participants.keys())[0], list(self.participants.values())[0]

                text = f"<@!{winner_id}>, You are the last player standing with **{winner_points}** points!"
                if self.is_tournament:
                    await self.update_tournament_lb(winner_id) 
                    text += f"\n\nAs the sole survivor, you will receive 💸 **{self.prize_pool:,}**!"
                    if self.unbelievaboat_api_enabled:
                        await self.client.addcoins(winner_id, self.prize_pool, "Sole surviver of Minecraft Madness Tournament")
                else:
                    await self.update_casual_lb(winner_id) 
                    if self.give_10k_to_winner:
                        text += f"\n\nAs the sole survivor, you will receive 💸 **10,000**!"

                        if self.unbelievaboat_api_enabled:
                            await self.client.addcoins(winner_id, 10000, "Won in a Minecraft Madness game with 5+ participants")
                    
                win_em = discord.Embed(title="Game Over!", description=text, color=self.client.failure)
                win_em.set_thumbnail(url=self.client.user.avatar_url_as(static_format="png", size=2048))


                await self.clear_variables()
                await self.event_channel.send(embed=win_em)
                await self.event_channel.send("Check the win leaderboard with `/lb`")
                return

            self.users_guessed = []; self.eliminated = []


    @tasks.loop(minutes=470)
    async def tournamet(self):
        
        if not self.config["active"]:
            return

        await self.client.wait_until_ready()

        await self.tournament_channel.send(f"{self.ping_role_str}, a tournament will begin in 10 minutes. Get ready!", allowed_mentions=AllowedMentions(roles=True))

        await asyncio.sleep(600)

        if self.is_event_ongoing:

            while self.is_event_ongoing:
                await asyncio.sleep(1)

        self.is_tournament = True
        self.is_event_ongoing = True
        self.event_channel = self.tournament_channel

        await self.event_channel.send(self.ping_role_str, allowed_mentions=AllowedMentions(roles=True))

        await self.join_event(self.event_channel)

        while not self.members_ready:  # wait until everyone is ready
            await asyncio.sleep(1)

        self.prize_pool = len(self.participants.keys()) * 10000

        await self.main_event_func()
        
        self.is_event_ongoing = False


    async def handle_join_button(self, ctx):
        try:
            em = ctx.origin_message.embeds[0]
            self.game_cache["embed"] = em
        except IndexError:
            em = self.game_cache["embed"]

        if not self.participants:
            self.participants[ctx.author.id] = 0
            em.set_field_at(index=0, value=f"<@!{ctx.author_id}>", name=em.fields[0].name)
            self.all_game_participants[ctx.author.id] = 0
            self.game_cache["message"] = ctx.origin_message
            await ctx.edit_origin(embed=em)
            await ctx.send(embed=self.game_explanation, hidden=True)
            return

        elif ctx.author_id not in self.participants and self.participants:
            self.participants[ctx.author.id] = 0
            em.set_field_at(index=0, value=' | '.join([f'<@!{str(x)}>' for x in list(self.participants.keys())]), name=em.fields[0].name)
            self.all_game_participants[ctx.author.id] = 0
            self.game_cache["message"] = ctx.origin_message
            await ctx.edit_origin(embed=em)
            await ctx.reply(embed=self.game_explanation, hidden=True)

        else:
            await ctx.reply("You are already participating in this event!", hidden=True)
            return

        self.game_cache["embed"] = em

    async def return_difficulty(self):
        if self.game_cache["easy"] < 20 and self.game_cache["normal"] == 0 and self.game_cache["hard"] == 0:
            self.game_cache["easy"] += 1
            self.game_cache["total"] += 1
            return "easy"        

        elif self.game_cache["easy"] == 20 and self.game_cache["normal"] == 0 and self.game_cache["hard"] == 0:
            self.game_cache["normal"] += 1
            self.game_cache["total"] += 1
            return "normal"
        
        elif self.game_cache["normal"] < 10 and self.game_cache["easy"] == 20 and self.game_cache["hard"] == 0:
            self.game_cache["normal"] += 1
            self.game_cache["total"] += 1
            return "normal"
        elif self.game_cache["normal"] == 10 and self.game_cache["easy"] == 20 and self.game_cache["hard"] == 0:
            self.game_cache["hard"] += 1
            self.game_cache["total"] += 1
            return "hard"

        elif self.game_cache["easy"] == 20 and self.game_cache["normal"] == 10:
            self.game_cache["hard"] += 1
            self.game_cache["total"] += 1
            return "hard"

    async def prepare_question(self):
        difficulty = await self.return_difficulty()
        
        chosen_question = {}
        while 1:
            
            chosen_question = random.choice(list(self.quiz_data[difficulty]))
            if chosen_question not in self.used_questions:
                self.used_questions.append(chosen_question)
                break

        random.shuffle(self.quiz_data[difficulty][chosen_question]["options"])
        path = self.quiz_data[difficulty][chosen_question]
        desc = ""
        option_buttons = []
        labels = ["A", "B", "C"]
        for pos in range(len(path["options"])):
            if path["options"][pos].lower().strip() == path["answer"].lower().strip():
                self.correct_answer = f"option_{pos}"
                self.correct_option = labels[pos]

            desc += f"`{labels[pos]}) {path['options'][pos]}`\n\n"
            option_buttons.append(
                manage_components.create_button(
                    style=ButtonStyle.blue,
                    label=labels[pos],
                    custom_id=f"option_{pos}"
                ))

        sleep_time = [20, 10]
        if (5 < self.game_cache["easy"] <= 10) and self.game_cache["normal"] == 0 and self.game_cache["hard"] == 0:
            sleep_time = [15, 10]
        elif (11 <= self.game_cache["easy"] <= 15) and self.game_cache["normal"] == 0 and self.game_cache["hard"] == 0:
            sleep_time = [10, 10]
        elif (16 <= self.game_cache["easy"] <= 20) and self.game_cache["normal"] == 0 and self.game_cache["hard"] == 0:
            sleep_time = [10, 5]

        em = discord.Embed(color=self.client.failure, title=chosen_question, description=desc)
        em.set_author(name=f"Difficulty: {difficulty.lower().title()} | Level {len(self.used_questions)}",
        icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
        em.set_footer(text=f"⏳ Try to answer it within {sleep_time[0] + sleep_time[1]} seconds", icon_url=self.client.png)
        
        return em, [manage_components.create_actionrow(*option_buttons)], sleep_time


    async def handle_correct_answer(self, ctx):
        await ctx.defer(hidden=True)
        
        if ctx.author_id in self.users_guessed:
            em = discord.Embed(color=self.client.failure, description=f"Your current score is: **{self.all_game_participants[ctx.author_id]}**")
            em.set_author(name="You already answered this question.",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        elif (ctx.author_id in self.eliminated):
            em = discord.Embed(color=self.client.failure, description=f"Your score: **{self.all_game_participants[ctx.author_id]}**")
            em.set_author(name="You are already disqualified from the game!",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)
        
        elif (ctx.author_id not in self.participants.keys()) and (
            ctx.author_id in self.all_game_participants.keys()):
            em = discord.Embed(color=self.client.failure, description=f"Your score: **{self.all_game_participants[ctx.author_id]}**")
            em.set_author(name="You are already disqualified from the game!",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        elif (ctx.author_id not in self.all_game_participants.keys()):
            em = discord.Embed(color=self.client.failure)
            em.set_author(name="You cannot participate in this event right now.",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        if datetime.utcnow().timestamp() - self.question_start_ts <= 5:
            if not self.users_guessed:
                self.participants[ctx.author_id] += 30
            elif len(self.users_guessed) == 1:
                self.participants[ctx.author_id] += 25
            elif len(self.users_guessed) == 2:
                self.participants[ctx.author_id] += 20
            else:
                self.participants[ctx.author_id] += 10

        elif datetime.utcnow().timestamp() - self.question_start_ts <= 15:
            if not self.users_guessed:
                self.participants[ctx.author.id] += 20
            elif len(self.users_guessed) == 1:
                self.participants[ctx.author_id] += 19
            elif len(self.users_guessed) == 2:
                self.participants[ctx.author_id] += 18
            elif len(self.users_guessed) == 3:
                self.participants[ctx.author_id] += 15
            elif len(self.users_guessed) == 4:
                self.participants[ctx.author_id] += 14
            elif len(self.users_guessed) == 5:
                self.participants[ctx.author_id] += 13
            elif len(self.users_guessed) == 6:
                self.participants[ctx.author_id] += 12
            elif len(self.users_guessed) == 7:
                self.participants[ctx.author_id] += 11
            elif len(self.users_guessed) == 8:
                self.participants[ctx.author_id] += 10
            else:
                self.participants[ctx.author_id] += 5
        
        elif datetime.utcnow().timestamp() - self.question_start_ts <= 30:
            if not self.users_guessed:
                self.participants[ctx.author.id] += 10
            elif len(self.users_guessed) == 1:
                self.participants[ctx.author_id] += 9
            elif len(self.users_guessed) == 2:
                self.participants[ctx.author_id] += 8
            elif len(self.users_guessed) == 3:
                self.participants[ctx.author_id] += 5
            elif len(self.users_guessed) == 4:
                self.participants[ctx.author_id] += 4
            elif len(self.users_guessed) == 5:
                self.participants[ctx.author_id] += 3
            elif len(self.users_guessed) == 6:
                self.participants[ctx.author_id] += 2
            else:
                self.participants[ctx.author_id] += 1

        self.all_game_participants[ctx.author_id] = self.participants[ctx.author_id]
        self.users_guessed.append(ctx.author_id)

        em = discord.Embed(color=self.client.failure)
        em.set_author(name="Your answer is correct! You're moving on to the next round.", 
        icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))

        return await ctx.reply(embed=em, hidden=True)


    async def handle_incorrect_answer(self, ctx):
        await ctx.defer(hidden=True)

        if (ctx.author.id not in self.participants.keys()) and (ctx.author.id not in self.all_game_participants.keys()):
            em = discord.Embed(color=self.client.failure)
            em.set_author(name="You cannot participate in this event right now.",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        if ctx.author_id in self.users_guessed and ctx.author_id in self.participants.keys():
            em = discord.Embed(color=self.client.failure)
            em.set_author(name="You already answered this question.",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        if (ctx.author_id not in self.eliminated) and (ctx.author_id not in self.users_guessed) and (ctx.author.id in self.all_game_participants.keys()):
            
            try:
                self.all_game_participants[ctx.author_id] = self.participants[ctx.author_id]
            except KeyError:
                pass
            
            em = discord.Embed(color=self.client.failure, description="You are now eliminated from the game!\n"
            f"You accumulated a total of **{self.all_game_participants[ctx.author_id]}** points.")
            em.set_author(name=f"Wrong Answer, it was {self.correct_option}",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            
            try:
                self.all_game_participants[ctx.author_id] = self.participants[ctx.author_id]
  
                await ctx.reply(embed=em, hidden=True)
                self.eliminated.append(ctx.author_id)

                await self.event_channel.send(embed=(discord.Embed(description=f"**{ctx.author.name}** was disqualified with **{self.all_game_participants[ctx.author_id]}**\n**{len(self.participants) - len(self.eliminated)}** players remaining", color=self.client.failure).set_author(name="R.I.P",
                icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))), delete_after=5)
                return
            
            except KeyError:
                em = discord.Embed(color=self.client.failure, description=f"Your score: **{self.all_game_participants[ctx.author_id]}**")
                em.set_author(name="You are already disqualified from the game!",
                icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
                return await ctx.reply(embed=em, hidden=True)

        elif ctx.author_id in self.all_game_participants.keys() and ctx.author_id in self.eliminated:
            em = discord.Embed(color=self.client.failure, description=f"Your score: **{self.all_game_participants[ctx.author_id]}**")
            em.set_author(name="You are already disqualified from the game!",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

        else:
            em = discord.Embed(color=self.client.failure)
            em.set_author(name="You cannot participate in this event right now.",
            icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
            return await ctx.reply(embed=em, hidden=True)

    @commands.Cog.listener()
    async def on_component(self, ctx:ComponentContext):
        if ctx.custom_id == "i_joined":
            await self.handle_join_button(ctx)
        
        elif ctx.custom_id == self.correct_answer:
            await self.handle_correct_answer(ctx)

        elif ctx.custom_id in ["option_0", "option_1", "option_2"] and ctx.custom_id != self.correct_answer:
            await self.handle_incorrect_answer(ctx)

        elif str(ctx.custom_id).startswith("paginator__"):
            if datetime.utcnow().timestamp() - int(float(str(ctx.custom_id).replace("paginator__", "")[:-2])) > 30:
                return await ctx.send("Button timed out. Please run the command again!", hidden=True)


    @cog_slash(name='mm', guild_ids=const.slash_guild_ids, description='Start a Minecraft Madness game')
    async def mm(self, ctx: SlashContext):
    
        await self.client.wait_until_ready()

        await ctx.defer(hidden=True)
    
        if self.is_event_ongoing:
            return await ctx.send("Sorry, a game is already in progress. Please wait until it's finished before starting a new one", hidden=True)
        self.is_tournament = False

        self.event_channel = self.mm_channel

        self.is_event_ongoing = True
        
        if not ctx.channel_id == self.event_channel.id:
            await ctx.channel.send(f"A 'Minecraft Madness' event has started in <#{self.event_channel.id}>. Head there to join the fun!")

        await ctx.send("Success!", hidden=True)

        await self.join_event(self.event_channel)
        
        while not self.members_ready:  # wait until everyone is ready
            await asyncio.sleep(1)

        if len(self.participants) >= 5:
            self.give_10k_to_winner = True

        await self.main_event_func()

        self.is_event_ongoing = False


    @cog_slash(name="mm_add", description="[ADMIN] Add a new question to the Minecraft Madness Quiz Game", guild_ids=const.slash_guild_ids, 
    options=[
        create_option(name="question", description="The question that players will have to answer", option_type=3, required=True) | {"focused": True},
        create_option(name="difficulty", description="The difficulty leve of the question", option_type=3, required=True, choices=[
            create_choice(value="easy", name="Easy"),
            create_choice(value="normal", name="Normal"),
            create_choice(value="hard", name="Hard")
        ]),
        create_option(name="answer", description="The correct answer to the question", option_type=3, required=True),
        create_option(name="first_incorrect_option", description="The first incorrect option", option_type=3, required=True),
        create_option(name="second_incorrect_option", description="The second incorrect option (Do not fill if the question is a True/False question", option_type=3,
        required=False)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def mm_add(self, ctx:SlashContext, question:str=None, difficulty:str=None, answer:str=None, first_incorrect_option:str=None, second_incorrect_option:str=None):
        await ctx.defer(hidden=True)
        
        params = locals()

        opts = [v for k, v in params if k in params.keys()[-3] and v]

        with open("data/games/quiz_questions.json", "w", encoding="utf8") as f:
            self.quiz_data[difficulty][question] = {
                "options": opts,
                "answer": answer}
            json.dump(self.quiz_data, f, indent=2)
        
        text = (
            f"New Question Added:\n"
            f"> Question: {question}\n"
            f"> Difficulty: {difficulty.capitalize()}\n"
            f"> Correct Answer: {answer}\n"
            f"> First Incorrect Answer: {first_incorrect_option}")
        text += f"\n> Second Incorrect Answer: {second_incorrect_option}" if second_incorrect_option else ""

        return await ctx.send(text, hidden=True)

    
    @cog_slash(name='mm_edit', description='[ADMIN] Edit an existing question.', guild_ids=const.slash_guild_ids, 
     options=[
        create_option("question_to_edit", "The question to edit", 3, True) | {"focused": True},
        create_option('difficulty', 'The difficulty level of the question', 3, True, choices=[
            create_choice(value="easy", name="Easy"),
            create_choice(value="normal", name="Normal"),
            create_choice(value="hard", name="Hard")
            ]),
        create_option("new_question", "The new questions to be asked in the game", 3, True),
        create_option("answer", "The correct answer to the question", 3, True),
        create_option("first_incorrect_option", "The first incorrect option", 3, True),
        create_option("second_incorrect_option", "The second incorrect option (Do not fill if the question is a True/False question", 3, False)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def mm_edit(self, ctx:SlashContext, question_to_edit:str=None, difficulty:str=None, new_question:str=None, answer:str=None, first_incorrect_option:str=None, second_incorrect_option:str=None):
        await ctx.defer(hidden=True)
        
        if not self.quiz_data[difficulty].pop(question_to_edit, False):
            return await ctx.send(f"The question `{question_to_edit}` doesn't exst in the `{difficulty.capitalize()}` difficulty questions", hidden=True)
        
        params = locals()
        opts = [v for k, v in params if k in params.keys()[-3] and v]

        with open("data/games/quiz_questions.json", "w", encoding="utf8") as f:
            self.quiz_data[difficulty][question_to_edit] = {
                "options": opts,
                "answer": answer}
            json.dump(self.quiz_data, f, indent=2)
        
        text = (
            f"Question data changed to:\n"
            f"> Question: {question_to_edit}\n"
            f"> Difficulty: {difficulty.capitalize()}\n"
            f"> Correct Answer: {answer}\n"
            f"> First Incorrect Answer: {first_incorrect_option}")
        text += f"\n> Second Incorrect Answer: {second_incorrect_option}" if second_incorrect_option else ""

        return await ctx.send(text, hidden=True)


    @cog_slash(name='mm_delete', description='[ADMIN] Delete a question from the questions bank.', guild_ids=const.slash_guild_ids, options=[
        create_option('difficulty', 'The difficulty level of the question', 3, True),
        create_option("question_to_delete", "The question to delete", 3, True),
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def delete(self, ctx: SlashContext, difficulty:str=None, question_to_delete:str=None):
        await ctx.defer(hidden=True)

        if not self.quiz_data[difficulty].pop(question_to_delete, False):
            return await ctx.send(f"The question `{question_to_delete}` doesn't exst in the `{difficulty.capitalize()}` difficulty.", hidden=True)
                
        with open("data/games/quiz_questions.json", "w", encoding="utf8") as f:
            json.dump(self.quiz_data, f, indent=2)
        
        return await ctx.send(f"Deleted `{question_to_delete}` from the {difficulty.capitalize()} questions.", hidden=True)

    
    @cog_slash(name="mm_questions", description="[ADMIN] Display all Minecraft Madness questions and answers", guild_ids=const.slash_guild_ids, options=[
        create_option(name="difficulty", description="Display questions and answers for a specific difficulty", option_type=3, required=True, choices=[
            create_choice(value="easy", name="Easy"),
            create_choice(value="normal", name="Normal"),
            create_choice(value="hard", name="Hard")
        ]) | {"focused": True}])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def mm_questions(self, ctx:SlashContext, difficulty:str=None):
        await ctx.defer(hidden=True)
        
        ranked = [key for key in self.quiz_data[difficulty].keys()]

        embeds = []

        add_on = [y for y in range(9, len(self.quiz_data[difficulty]), 10)] if len(self.quiz_data[difficulty]) >= 10 else [len(self.quiz_data[difficulty])-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.quiz_data[difficulty])-1)
        
        em = discord.Embed(color=self.client.failure, title=f"Minecraft Madness Q & A's ({difficulty.capitalize()})", description="")
        
        for x in range(len(self.quiz_data[difficulty])):
            
            question = ranked[x]
            answer = self.quiz_data[difficulty][ranked[x]]["answer"]
            
            options_txt = ""
            for index, option in enumerate([opt for opt in self.quiz_data[difficulty][ranked[x]]["options"] if opt != answer]):
                if option == answer:
                    continue
                options_txt += f"> Option {index+1}: {option}\n"
            
            em.description += f"**{x+1}. {question}**\n"
            em.description += f"> Answer: {answer}\n"
            em.description += options_txt + "\n"

            if x in add_on:
                em.set_footer(text=f"TitanMC | Minecraft Madness | Page {add_on.index(x)+1}/{len(add_on)}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=self.client.failure, title=f"Minecraft Madness Q & A's ({difficulty.capitalize()})", description="")

        await Paginator(embeds, ctx).run()

    @cog_slash(name="mm_config", description="[ADMIN] Configure Minecraft Madness", guild_ids=const.slash_guild_ids, options=[
        create_option(name="active", description="Activate or deactivate Minecraft Madness", option_type=5, required=False),
        create_option(name="tournament_channel", description="Channel where tournaments will take place", option_type=7, required=False),
        create_option(name="ping_role", description="The role that will be pinged for tournament notifications", option_type=8, required=False),
        create_option(name="casual_channel", description="Channel where casual games will take place", option_type=7, required=False),
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def mm_config(self, ctx:SlashContext, active:bool=None, tournament_channel:discord.TextChannel=None, ping_role:discord.Role=None, casual_channel:discord.TextChannel=None):
        
        await ctx.defer(hidden=True)

        text = "Config settings:\n"

        if active is not None:
            if active == self.config["active"]:
                text += f"> Activated: Already set to `{active}`\n"
            else:
                self.config["active"] = active
                text += f"> Activated: Set to `{active}`\n"
        else:
            text += f"> Activated: `{active}` (unchanged)\n"

        if tournament_channel:
            if tournament_channel.id != self.config["tournament_id"]:
                if isinstance(tournament_channel, discord.VoiceChannel):
                    return await ctx.send("Channel must be a Text Channel, not a Voice Channel!", hidden=True)

                self.config["tournament_id"] = tournament_channel.id
                self.main_ch = tournament_channel
                text += f"> Tournament Channel: Set to <#{tournament_channel.id}>"
            else:
                text += f"> Tournament Channel: Already set to <#{self.config['tournament_id']}>\n"
        
        else:
            text += f"> Tournament Channel: <#{self.config['tournament_id']}> (unchanged)\n"

        if ping_role:
            if ping_role.id != self.config["ping_role_id"]:
                self.config["ping_role_id"] = ping_role.id
                self.ping_role_str = f"<@&{ping_role.id}>"

        if casual_channel:
            if casual_channel.id != self.config["mm_channel_id"]:
                if isinstance(casual_channel, discord.VoiceChannel):
                    return await ctx.send("Channel must be a Text Channel, not a Voice Channel!", hidden=True)

                self.config["mm_channel_id"] = casual_channel.id
                self.main_ch = casual_channel
                text += f"> Casual Channel: Set to <#{casual_channel.id}>\n"
            else:
                text += f"> Casual Channel: Already set to <#{self.config['mm_channel_id']}>\n"
        
        else:
            text += f"> Casual Channel: <#{self.config['mm_channel_id']}> (unchanged)"

        with open("data/games/mm_config.json", "w") as f:
            json.dump(self.config, f, indent=2)

        if self.tournamet.is_running():
            self.tournamet.cancel()
        
        self.get_ready.start()

        return await ctx.send(text, hidden=True)

def setup(client):
    client.add_cog(McMadness(client))
    