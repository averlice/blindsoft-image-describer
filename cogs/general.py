import discord
from discord.ext import commands
import time

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", description="Checks the bot's latency and status.")
    async def ping(self, ctx: commands.Context):
        start_time = time.time()
        # Send a "thinking" message
        message = await ctx.send("Pinging...")
        end_time = time.time()

        latency_discord_api = round(self.bot.latency * 1000)
        latency_command_response = round((end_time - start_time) * 1000)

        uptime_seconds = time.time() - self.bot.start_time if hasattr(self.bot, 'start_time') else 0
        uptime_minutes, uptime_seconds = divmod(uptime_seconds, 60)
        uptime_hours, uptime_minutes = divmod(uptime_minutes, 60)
        uptime_days, uptime_hours = divmod(uptime_hours, 24)

        status_message = (
            f"**Pong!**\n"
            f"Discord API Latency: `{latency_discord_api}ms`\n"
            f"Command Response Latency: `{latency_command_response}ms`\n"
            f"Uptime: `{int(uptime_days)}d {int(uptime_hours)}h {int(uptime_minutes)}m {int(uptime_seconds)}s`"
        )
        await message.edit(content=status_message)



async def setup(bot):
    await bot.add_cog(General(bot))