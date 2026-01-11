import discord
from discord.ext import commands
import os
import asyncio
import time
import logging
from config import DISCORD_BOT_TOKEN, OWNER_ID
import utils

# --- Logging Setup ---
# This configures logging to file (bot.log) AND console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

def get_prefix(bot, message):
    return utils.get_setting("prefix")

# Subclassing Bot to use setup_hook
class GeminiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, intents=intents, owner_id=OWNER_ID)
        self.start_time = None

    async def setup_hook(self):
        # Load cogs here to ensure it only happens once
        initial_extensions = [
            'cogs.general',
            'cogs.gemini',
            'cogs.admin',
            'cogs.ocr'
        ]
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded cog: {extension}")
            except Exception as e:
                await handle_error(f"Failed to load cog {extension}: {e}")

# Initialize the bot
bot = GeminiBot()

# Centralized error handler
async def handle_error(error_message: str):
    logger.error(error_message) # Log to file/console
    
    settings = utils.load_settings()
    error_log_dm = settings.get("error_log_dm")
    error_log_channel_id = settings.get("error_log_channel_id")

    if error_log_dm:
        try:
            owner = await bot.fetch_user(OWNER_ID)
            if owner:
                await owner.send(f"**Bot Error:**\n```\n{error_message}\n```")
        except Exception as e:
            logger.error(f"Failed to send error DM to owner: {e}")
            
    if error_log_channel_id:
        try:
            channel = bot.get_channel(error_log_channel_id)
            if channel:
                await channel.send(f"**Bot Error:**\n```\n{error_message}\n```")
        except Exception as e:
            logger.error(f"Failed to send error to channel: {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")
    if bot.start_time is None:
        bot.start_time = time.time()
    
    print("Bot is ready.")
    # DM the owner on startup
    try:
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            await owner.send("haha i'm here to conker all of india!")
            logger.info("Sent startup DM to owner.")
        else:
            await handle_error("Could not find owner to send startup DM.")
    except Exception as e:
        await handle_error(f"Failed to send startup DM: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass 
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the necessary permissions to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the necessary permissions to execute this command.")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("This command can only be used by the bot owner.")
    elif isinstance(error, commands.CheckFailure):
         await ctx.send("A check failed for this command. You may not have permission.")
    else:
        # For other errors, log them using our new handler
        await handle_error(f"An unexpected error occurred in command '{ctx.command}': {error}")
        await ctx.send("An unexpected error occurred. The bot owner has been notified.")

# Run the bot
async def main():
    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN is None:
        print("Error: DISCORD_BOT_TOKEN is not set. Please check your .env file.")
    else:
        asyncio.run(main())