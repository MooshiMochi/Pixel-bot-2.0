import discord
import asyncio

from random import choice

from discord.ext import commands

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

from constants import const


class TicTacToe(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    async def create_box(self, board:list=[], win_coords:tuple=()):
        rows = []
        for y, row in enumerate(board):
            buttons = []
            for x, status in enumerate(row):
                buttons.append(
                    create_button(
                        style=ButtonStyle.green if (x, y) in win_coords else ButtonStyle.grey if status == 0 else ButtonStyle.red if status == -1 else ButtonStyle.blue if status == 1 else  ButtonStyle.grey,
                        label="\u200b" if status == 0 else "X" if status == -1 else "O" if status == 1 else "\u200b",
                        custom_id=f"TicTacToeBtn_{status}_{x}{y}"
                    )
                )
            rows.append(create_actionrow(*buttons))
            buttons = []
        return rows

    async def check_for_winner(self, board:list=[]):
        for across in board:
            value = sum(across)
            if value == 3:
                y_val = board.index(across)
                return "O", ((0, y_val), (1, y_val), (2, y_val))
            elif value == -3:
                y_val = board.index(across)
                return "X", ((0, y_val), (1, y_val), (2, y_val))

        # Check vertical
        for line in range(3):
            value = board[0][line] + board[1][line] + board[2][line]
            if value == 3:
                return "O", ((line, 0), (line, 1), (line, 2))
            elif value == -3:
                return "X", ((line, 0), (line, 1), (line, 2))

        # Check diagonals
        diag = board[0][2] + board[1][1] + board[2][0]
        if diag == 3:
            return "O", ((2, 0), (1, 1), (0, 2))
        elif diag == -3:
            return "X", ((2, 0), (1, 1), (0, 2))

        diag = board[0][0] + board[1][1] + board[2][2]
        if diag == 3:
            return "O", ((0, 0), (1, 1), (2, 2))
        elif diag == -3:
            return "X", ((0, 0), (1, 1), (2, 2))

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in board for i in row):
            return "XO", ()

        return None, ()

    
    @cog_slash(name="tic_tac_toe", description="Challenge someone to a tic tac toe game", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The person to challenge", option_type=6, required=True)
    ])
    async def tic_tac_toe(self, ctx:SlashContext, member:discord.Member=None):

        if "game" not in ctx.channel.name.lower():
            warn = discord.Embed(description="You can use this command in game channels only.", color=self.client.failure)
            warn.set_footer(text="TN | Tic Tac Toe", icon_url=self.client.png)
            return await ctx.send(embed=warn, hidden=True)

        if ctx.author_id == member.id:
            return await ctx.send("You cannot challenge yourself to a tic tac toe game.", hidden=True)
        
        elif member.id == self.client.user.id:
            return await ctx.send("Sorry, I don't have time at the moment.", hidden=True)

        elif member.bot:
            return await ctx.send(f"It would be weird if {member} could play, don't you think?", hidden=True)
        
        BOARD = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ]
        
        X = -1
        O = 1

        Player = choice([X, O])

        gameEnded = False
        winCoords = ()

        msg = await ctx.send("⌛ Your game is loading...")

        components = await self.create_box(BOARD, winCoords)

        em = discord.Embed(color=self.client.failure, description=f"**{ctx.author}** challenged **{member.mention}** to a Tic Tac Toe game!\n\nIf either one of the players does not respond within 5 mins, the game will be cancelled!",
        title=f"X's turn." if Player == -1 else "O's turn")
        em.set_footer(text="TN | Tic Tac Toe", icon_url=self.client.png)
        em.set_author(name="❌⭕ Tic Tac Toe")

        em.description += f"\n\n**{ctx.author}** is X's\n**{member}** is O's"

        await msg.edit(content=None, embed=em, components=components)

        while 1:
            try:
                btnCtx: ComponentContext = await wait_for_component(self.client, msg, timeout=300)

                if btnCtx.author_id != ctx.author_id and btnCtx.author_id != member.id:
                    await btnCtx.send("You can not interact with this game. Please start your own to do so!", hidden=True)
                    continue

                if gameEnded:
                    await btnCtx.send("This game has ended. Please start a new one!", hidden=True)
                    continue

                if (Player == X and (btnCtx.author_id != ctx.author_id)) or (Player == O and (btnCtx.author_id != member.id)):
                    await btnCtx.send("It is not your turn yet. Wait for the O's to make their move.", hidden=True)
                    continue

                _btn, _status, _xy = btnCtx.custom_id.split("_")
                status = int(_status)
                x, y = int(_xy[0]), int(_xy[1])

                if status != 0:
                    await btnCtx.send("That position is already occupied!", hidden=True)
                    continue

                BOARD[y][x] = X if Player == X else O

                Player = X if Player == O else O

                winner, winCoords = await self.check_for_winner(BOARD)

                new_rows = await self.create_box(BOARD, winCoords)

                if winner:
                    gameEnded = True

                    if winner == "XO":
                        await ctx.send(f"It looks like it's a tie! ||{ctx.author.mention} {member.mention}||")
                        em.title = f"🏆 Tie game!"

                    elif winner == "X":
                        await ctx.send(f"{ctx.author.mention} won! ||{ctx.author.mention} {member.mention}||")
                        em.title = f"🏆 {ctx.author} won!"

                    elif winner == "O":
                        await ctx.send(f"{member.mention} won! ||{ctx.author.mention} {member.mention}||")
                        em.title = f"🏆 {member} won!"

                await btnCtx.edit_origin(embed=em, components=new_rows)

            except asyncio.TimeoutError:
                em.title = "⏲️ Game ended due to inactivity"
                gameEnded = True
                await msg.edit(embed=em, components=[], content=None)
                return


def setup(client):
    client.add_cog(TicTacToe(client))
