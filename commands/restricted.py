from sre_constants import OP_IGNORE
import subprocess
import asyncio
from discord.ext import commands
import discord
from constants import const
import io
import traceback
import textwrap
import os
from utils.paginator import TextPageSource, Paginator as paginator
from contextlib import redirect_stdout
from discord_slash.cog_ext import cog_slash
from discord_slash import SlashContext
from discord_slash.utils.manage_commands import create_option


class Restricted(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client
        self._last_result = None

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.client.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')


    @commands.group(
        help="Developer tools.",
        brief="Dev tools.",
        aliases=['d', 'dev']
    )
    @commands.is_owner()
    async def developer(self, ctx):
        if ctx.invoked_subcommand is None:
            embed=discord.Embed(title="Hmmm...", 
                                description=f"You seem lost. Try to use / for more commands.",
                                color=self.client.failure)
            await ctx.embed(embed=embed)

    @developer.command(
        name='sync',
        help="Sync with GitHub and reload cogs.",
        brief="Sync with GitHub and reload cogs."
    )
    @commands.is_owner()
    async def developer_sync(self, ctx):
        out = subprocess.check_output("git pull", shell=True)
        embed=discord.Embed(title="git pull",
                            description=f"```py\n{out.decode('utf8')}\n```",
                            color=self.client.success)
        await ctx.embed(embed)

        for ext in const.command_exts:
            self.client.unload_extension(ext)

        for dir_name in ["events"]:
            for file in os.listdir(dir_name):
                if file.endswith(".py"):
                        self.client.unload_extension(f"{dir_name}.{file}".replace('.py', ''))
                        self.client.load_extension(f"{dir_name}.{file}".replace('.py', ''))

        skipped = 0
        for dir_name in ["utils"]:
            for file in os.listdir(dir_name):
                if file.endswith(".py"):
                    try:
                        self.client.load_extension(f"{dir_name}.{file}".replace('.py', ''))
                    except (commands.NoEntryPointError, commands.ExtensionAlreadyLoaded) as e:
                        self.client.logger.debug(f"Extension {dir_name}.{file.replace('.py', '')} not loaded: {e}")
                        skipped += 1
        self.client.logger.info('Client reloaded.')

    @developer.command(
        name='shell',
        help="Run something in shell.",
        brief="Run something in shell.",
        aliases=['sh']
    )
    @commands.is_owner()
    async def developer_shell(self, ctx, *, command):
        async with ctx.typing():
            stdout, stderr = await self.run_process(command)

        if stderr:
            await ctx.message.add_reaction(self.client.no)
            text = f'stdout:\n{stdout}\nstderr:\n{stderr}'
        else:
            await ctx.message.add_reaction(self.client.yes)
            text = stdout

        pages = TextPageSource(text).getPages()
        await paginator(pages, ctx).run()

    @developer.command(
        name='eval',
        help="Run something in python shell.",
        brief="Run something in python shell."
    )
    @commands.is_owner()
    async def dev_eval(self, ctx, *, code: str):
        env = {
            'discord': discord,
            'client': self.client,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'self': self,
            '_': self._last_result,
            'const': const
        }

        env.update(globals())

        code = self.cleanup_code(code)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(code, "    ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            pages = TextPageSource(str(e.__class__.__name__) + ': ' + str(e), code_block=True).getPages()
            if len(pages) == 1:
                await ctx.send(pages[0][:-8].strip())
            else:
                await paginator(pages, ctx).run()
            return
            
        else:
            func = env['func']

            try:
                with redirect_stdout(stdout):
                    ret = await func()
            except Exception as e:
                value = stdout.getvalue()
                pages = TextPageSource(value + str("".join(traceback.format_exception(e, e, e.__traceback__))), code_block=True).getPages()
                if len(pages) == 1:
                    await ctx.send(pages[0][:-8].strip())
                else:
                    await paginator(pages, ctx).run()
            else:
                value = stdout.getvalue()

                if ret is None and value != '':
                    pages = TextPageSource(value, code_block=True).getPages()
                    if len(pages) == 1:
                        await ctx.send(pages[0][:-8].strip())
                    else:
                        await paginator(pages, ctx).run()
                    return
                else:
                    self._last_result = ret
                    if value != '' or ret != '':
                        pages = TextPageSource(value + str(ret), code_block=True).getPages()
                        if len(pages) == 1:
                            await ctx.send(pages[0][:-8].strip())
                        else:
                            await paginator(pages, ctx).run()


    @cog_slash(name="error", description="[DEVELOPER] Raises ValueError", guild_ids=const.slash_guild_ids, options=[
        create_option(name="error_message", description="The error message to return", option_type=3, required=False)])
    @commands.is_owner()
    async def _raise_error(self, ctx:SlashContext, error_message:str="No error message"):
        
        raise ValueError(error_message)


def setup(client):
    client.add_cog(Restricted(client))
