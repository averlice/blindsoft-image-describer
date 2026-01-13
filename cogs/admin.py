import discord
from discord.ext import commands, tasks
from google import genai
import utils
import os
import subprocess
import asyncio
from config import GEMINI_API_KEY, OWNER_IDS

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize client here for listmodels
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.update_available = False
        self.auto_update_task.start()
        self.bot.loop.create_task(self.startup_check())

    def cog_unload(self):
        self.auto_update_task.cancel()

    async def startup_check(self):
        await self.bot.wait_until_ready()
        if utils.get_setting("auto_update"):
            print("[Startup] Checking for updates...")
            try:
                await asyncio.create_subprocess_shell("git fetch", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                process = await asyncio.create_subprocess_shell(
                    "git rev-list HEAD..@{u} --count",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                output = stdout.decode().strip()
                
                if output and output.isdigit() and int(output) > 0:
                    print(f"[Startup] Found {output} updates. Applying...")
                    await self.perform_update("Startup Auto-Update")
                else:
                    print("[Startup] Bot is up to date.")
            except Exception as e:
                print(f"[Startup] Update check failed: {e}")
                await self.report_error(f"Startup Update Check Failed: {e}")

    async def perform_update(self, context_name):
        """Shared update logic for manual and auto updates."""
        try:
            # 1. Stash
            stash_proc = await asyncio.create_subprocess_shell("git stash", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await stash_proc.communicate()
            
            # 2. Pull
            pull_proc = await asyncio.create_subprocess_shell(
                "git pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await pull_proc.communicate()
            pull_output = stdout.decode().strip()
            pull_error = stderr.decode().strip()

            result_msg = f"**{context_name} Result:**\n```\n{pull_output}\n```"
            
            # 3. Pop Stash
            pop_proc = await asyncio.create_subprocess_shell("git stash pop", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            pop_out, pop_err = await pop_proc.communicate()
            
            if pop_proc.returncode != 0:
                # Pop failed (conflict)
                result_msg += f"\n**Note:** Local changes were stashed but could not be re-applied due to conflicts. They are safe in `git stash`.\nPop Error: ```{pop_err.decode().strip()}```"
            elif b"No stash entries found" not in pop_err and b"Dropped" in pop_out:
                # Pop successful
                pass
            
            if pull_proc.returncode != 0 or pull_error:
                 result_msg += f"\n**Pull Errors:**\n```\n{pull_error}\n```"
                 await self.report_error(f"{context_name} Failed:\n{result_msg}")
            
            return result_msg

        except Exception as e:
            return f"Update Exception: {e}"

    async def report_error(self, error_message: str):
        """Helper to send errors to configured log channels and DMs."""
        print(f"[Error Report] {error_message}") # Console log
        
        settings = utils.load_settings()
        error_log_dm = settings.get("error_log_dm")
        error_log_channel_id = settings.get("error_log_channel_id")
        
        if error_log_dm:
            for owner_id in OWNER_IDS:
                try:
                    owner = await self.bot.fetch_user(owner_id)
                    if owner:
                        await owner.send(f"**Bot Error:**\n```\n{error_message}\n```")
                except Exception as e:
                    print(f"Failed to send error DM to {owner_id}: {e}")

        if error_log_channel_id:
            try:
                channel = self.bot.get_channel(error_log_channel_id)
                if channel:
                    await channel.send(f"**Bot Error:**\n```\n{error_message}\n```")
            except Exception as e:
                print(f"Failed to send error to channel: {e}")

    @commands.command(name="conlog", description="Sends the last 20 lines of the console log to a specific channel (Owner Only).")
    @commands.is_owner()
    async def conlog(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Sends the last 20 lines of the console log to a specific channel.
        Usage: conlog <#channel_or_id>
        """
        log_file = "bot.log"
        if not os.path.exists(log_file):
            await ctx.send("No log file found.")
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_lines = lines[-20:]
                log_content = "".join(last_lines)
            
            if not log_content.strip():
                await ctx.send("Log file is empty.")
                return
                
            if len(log_content) > 1900:
                log_content = log_content[-1900:]
            
            await channel.send(f"**Console Log (Last 20 lines):**\n```\n{log_content}\n```")
            await ctx.send(f"Logs sent to {channel.mention}.")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}.")
        except Exception as e:
            await ctx.send(f"Failed to read/send log file: {e}")
            await self.report_error(f"Failed to execute conlog: {e}")

    @tasks.loop(hours=1)
    async def auto_update_task(self):
        if utils.get_setting("auto_update"):
            try:
                await asyncio.create_subprocess_shell("git fetch", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                process = await asyncio.create_subprocess_shell(
                    "git rev-list HEAD..@{u} --count",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                output = stdout.decode().strip()
                
                if output and output.isdigit() and int(output) > 0:
                    msg = await self.perform_update("Hourly Auto-Update")
                    print(f"[Auto-Update] {msg}")
                    
            except Exception as e:
                print(f"[Auto-Update] Failed: {e}")
                await self.report_error(f"Auto-Update Exception: {e}")

    @auto_update_task.before_loop
    async def before_auto_update_task(self):
        await self.bot.wait_until_ready()

    @commands.command(name="updatecheck", description="Checks if updates are available (Owner Only).")
    @commands.is_owner()
    async def updatecheck(self, ctx: commands.Context):
        await ctx.send("Checking for updates...")
        try:
            # Fetch latest info
            await asyncio.create_subprocess_shell("git fetch", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            # Check for difference between HEAD and upstream
            process = await asyncio.create_subprocess_shell(
                "git rev-list HEAD..@{u} --count",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip()
            
            if output and output.isdigit() and int(output) > 0:
                self.update_available = True
                await ctx.send(f"**Updates Available:** {output} new commits found. You can now run `{ctx.prefix}update`.")
            elif output == "0":
                self.update_available = False
                await ctx.send("No updates available. The bot is up to date.")
            else:
                self.update_available = False
                await ctx.send(f"Could not determine update status. Output: {output}")
                
        except Exception as e:
            self.update_available = False
            await ctx.send(f"Failed to check for updates: {e}")
            await self.report_error(f"Update Check Failed: {e}")

    @commands.command(name="autoupdate", description="Toggles automatic hourly updates (Owner Only).")
    @commands.is_owner()
    async def autoupdate(self, ctx: commands.Context):
        current = utils.get_setting("auto_update")
        new_status = not current
        utils.update_setting("auto_update", new_status)
        status_str = "enabled" if new_status else "disabled"
        await ctx.send(f"Automatic hourly updates have been **{status_str}**.")

    @commands.command(name="update", description="Manually pulls updates from the repository (Owner Only).")
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        if not self.update_available:
            await ctx.send(f"No updates confirmed. Please run `{ctx.prefix}updatecheck` first.")
            return

        await ctx.send("Updates confirmed. Applying...")
        msg = await self.perform_update("Manual Update")
        
        if len(msg) > 2000:
            msg = msg[:1990] + "...\n```"
        await ctx.send(msg)
        
        # Reset state
        self.update_available = False

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