import discord
from discord.ext import commands
from google import genai
import utils
import os
from config import GEMINI_API_KEY

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize client here for listmodels
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    @commands.command(name="errorlog", description="Sets the channel for bot error logging (Owner Only).")
    @commands.is_owner()
    async def errorlog(self, ctx: commands.Context, channel: discord.TextChannel):
        utils.update_setting("error_log_channel_id", channel.id)
        await ctx.send(f"Error logs will now be sent to {channel.mention}.")

    @commands.command(name="errorlogdm", description="Toggles sending error logs to the owner's DMs (Owner Only).")
    @commands.is_owner()
    async def errorlogdm(self, ctx: commands.Context):
        current_status = utils.get_setting("error_log_dm")
        new_status = not current_status
        utils.update_setting("error_log_dm", new_status)
        
        status_text = "enabled" if new_status else "disabled"
        await ctx.send(f"Error logging to owner DMs has been {status_text}.")

    @commands.command(name="shutdown", description="Shuts down the bot (Owner Only).")
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.command(name="listmodels", description="Lists available Gemini models (Owner Only).")
    @commands.is_owner()
    async def listmodels(self, ctx: commands.Context):
        await ctx.send("Fetching available Gemini models...")
        try:
            model_list = []
            # New SDK listing
            for m in self.client.models.list():
                # Filter logic might need adjustment based on new SDK properties
                # For now, listing all and checking name
                model_list.append(f"- `{m.name}`")

            if model_list:
                # Chunking
                message_header = "**Available Models:**\n"
                current_chunk = message_header
                
                for model in model_list:
                    if len(current_chunk) + len(model) + 1 > 1900:
                        await ctx.send(current_chunk)
                        current_chunk = model + "\n"
                    else:
                        current_chunk += model + "\n"
                
                if current_chunk:
                    await ctx.send(current_chunk)
            else:
                await ctx.send("No models found.")
        except Exception as e:
            await ctx.send(f"An error occurred while listing models: {e}")
            from main import handle_error
            await handle_error(f"Failed to list Gemini models: {e}")

    @commands.command(name="prefix", description="Changes the bot's command prefix (Owner Only).")
    @commands.is_owner()
    async def prefix(self, ctx: commands.Context, new_prefix: str):
        """
        Changes the global prefix for the bot.
        Usage: prefix <new_prefix>
        Example: prefix !
        """
        if not new_prefix:
            await ctx.send("Please provide a new prefix.")
            return

        try:
            utils.update_setting("prefix", new_prefix)
            await ctx.send(f"Prefix updated to: `{new_prefix}`")
        except Exception as e:
            await ctx.send(f"Failed to update prefix: {e}")
            from main import handle_error
            await handle_error(f"Failed to update prefix setting: {e}")
            
    @commands.command(name="errorlogs", description="Shows the last 20 lines of the console error log (Owner Only).")
    @commands.is_owner()
    async def errorlogs(self, ctx: commands.Context):
        log_file = "bot.log"
        if not os.path.exists(log_file):
            await ctx.send("No log file found.")
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_lines = lines[-20:] # Get last 20 lines
                log_content = "".join(last_lines)
                
            if not log_content.strip():
                await ctx.send("Log file is empty.")
                return

            # Split into chunks if too long (Discord limit is 2000 chars)
            if len(log_content) > 1900:
                 log_content = log_content[-1900:] # Just take the very end if it's somehow massive
            
            await ctx.send(f"**Last 20 Log Lines:**\n```\n{log_content}\n```")

        except Exception as e:
            await ctx.send(f"Failed to read log file: {e}")

    @commands.command(name="say", description="Sends a message to a specific channel (Owner Only).")
    @commands.is_owner()
    async def say(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        """
        Sends a message to a specific channel.
        Usage: say <#channel_or_id> <message>
        Example: say #general Hello world!
        """
        try:
            await channel.send(message)
            # Optional: provide feedback to the owner that it was sent
            await ctx.message.add_reaction("✅")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}.")
        except Exception as e:
            await ctx.send(f"Failed to send message: {e}")

async def setup(bot):
    await bot.add_cog(Admin(bot))