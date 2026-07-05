import discord
from discord.ext import commands
from google import genai
from google.genai import types
from PIL import Image
import io
import aiohttp
from config import GEMINI_API_KEY
import asyncio
import re
import utils

# Helper function to send errors, defined outside the cog
async def send_error_log(bot, error_message):
    from main import handle_error
    await handle_error(error_message)

def truncate_message(message: str, max_length: int = 1900) -> str:
    """Truncates a message to fit Discord's character limit, adding an ellipsis if truncated. Kept for legacy/error use."""
    if len(message) > max_length:
        return message[:max_length - 3] + "..."
    return message


class GeminiCog(commands.Cog):
    def __init__(self, bot, client, model_name):
        self.bot = bot
        self.client = client
        self.model_name = model_name

    def _parse_flags(self, flags: str):
        model = self.model_name
        prompt = None
        
        # Match model flag: -m model_name (supports hyphens in model names like "gemini-3.5-flash")
        # Handles both quoted and unquoted model names
        model_match = re.search(r"-m\s+(?:([\"'])(.*?)\1|([^\s-][^\s]*))", flags)
        if model_match:
            model = model_match.group(2) or model_match.group(3)
            
        # Match prompt flag: -p "custom prompt" or --prompt "custom prompt"
        # Prioritizes quoted strings, falls back to unquoted text until next flag or end
        prompt_match = re.search(r"(?:-p|--prompt)\s+(?:([\"'])(.*?)\1|([^\s-]+(?:[^-]*)))", flags)
        if prompt_match:
            prompt = prompt_match.group(2) or prompt_match.group(3)
            if prompt:
                prompt = prompt.strip()
                
        return model, prompt

    async def _describe_image(self, channel, attachment, target_model, prompt=None):
        try:
            # Fetch image from URL
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        await send_error_log(self.bot, f"Failed to download image from {attachment.url} with status {resp.status}")
                        if hasattr(channel, 'send'):
                            await channel.send("Failed to download image. The error has been logged.")
                        return
                    image_bytes = await resp.read()

            # Prepare image for Gemini
            img = Image.open(io.BytesIO(image_bytes))

            # Send to Gemini
            final_prompt = prompt or "Describe this image in detail for a blind user, focusing on the key objects, colors, and the overall scene."
            response = self.client.models.generate_content(
                model=target_model,
                contents=[final_prompt, img]
            )

            # Safely get text content
            text_content = None
            try:
                if response and response.text:
                    text_content = response.text
            except Exception:
                pass

            if text_content:
                if hasattr(channel, 'send'):
                    await utils.send_long_message(channel, f"**Image Description ({target_model}):**\n{text_content}")
            else:
                await send_error_log(self.bot, f"Gemini API returned no text. Response: {response}")
                if hasattr(channel, 'send'):
                    await channel.send("Gemini API returned no description. The error has been logged.")

        except Exception as e:
            await send_error_log(self.bot, f"Exception during image description: {type(e).__name__}: {e}")
            if hasattr(channel, 'send'):
                await channel.send("An error occurred during image description. The error has been logged.")

    @commands.command(
        name="describe", 
        description="Describes an image using Gemini. Use -m for model and -p for a custom prompt.", 
        usage="[-m model] [-p \"prompt\"]",
        help="Describes an attached image. You can specify a model with '-m model_name' and a custom prompt with '-p \"your prompt\"'."
    )
    async def describe(self, ctx: commands.Context, *, flags: str = ""):
        if not self.client:
            await ctx.send("The Gemini client is not initialized. Please check the console for errors.")
            return

        if not ctx.message.attachments:
            await ctx.send("Please attach an image to the command message.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.content_type.startswith('image/'):
            await ctx.send("The attached file must be an image.")
            return

        target_model, custom_prompt = self._parse_flags(flags)

        async with ctx.typing():
            await self._describe_image(ctx, attachment, target_model, prompt=custom_prompt)
    
    @commands.command(
        name="scanimage",
        aliases=["simage"],
        description="Toggles automatic image description for all images posted in this server.",
        help="When toggled on, the bot will automatically describe any image posted in the server. Requires Manage Server permission."
    )
    @commands.has_permissions(manage_guild=True)
    async def scanimage(self, ctx: commands.Context):
        scan_guilds = utils.get_setting("scan_image_guilds")
        guild_id = ctx.guild.id
        
        if guild_id in scan_guilds:
            scan_guilds.remove(guild_id)
            utils.update_setting("scan_image_guilds", scan_guilds)
            await ctx.send("Automatic image scanning has been **disabled** for this server.")
        else:
            scan_guilds.append(guild_id)
            utils.update_setting("scan_image_guilds", scan_guilds)
            await ctx.send("Automatic image scanning has been **enabled** for this server. I will now describe any images posted here.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 1. Only process future messages (sent after bot started)
        if self.bot.start_time and message.created_at.timestamp() < self.bot.start_time:
            return

        # 3. Ignore if the message is a command to prevent double descriptions
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        scan_guilds = utils.get_setting("scan_image_guilds")
        if message.guild.id not in scan_guilds:
            return

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    # Use a background task to avoid blocking the listener
                    # Use the default model for automatic scans
                    asyncio.create_task(self._describe_image(message.channel, attachment, self.model_name))

    @commands.command(
        name="test", 
        description="Tests connection to Gemini API.", 
        usage="[-m model]",
        help="Tests if the bot can communicate with the Gemini API. You can optionally specify which model to test by adding '-m model_name'."
    )
    async def test(self, ctx: commands.Context, *, flags: str = ""):
        if not self.client:
            await ctx.send("The Gemini client is not initialized.")
            return
            
        target_model, _ = self._parse_flags(flags)
            
        await ctx.send(f"Testing connection to Gemini API with model: `{target_model}`")
        try:
            response = self.client.models.generate_content(
                model=target_model,
                contents="This is a test. Is the API working?"
            )
            
            # Safely get text content
            text_content = None
            try:
                if response and response.text:
                    text_content = response.text
            except Exception:
                pass

            if text_content:
                await ctx.send("Successfully connected to the Gemini API and received a response.")
            else:
                await ctx.send("Connected, but received an empty or unrecognized response structure. The error has been logged.")
                await send_error_log(self.bot, f"Gemini API test returned no text. Response: {response}")
        except Exception as e:
            error_type = type(e).__name__
            await ctx.send(f"Failed to connect to the Gemini API. Error ({error_type}): {e}")
            await send_error_log(self.bot, f"Gemini API test failed: {error_type}: {e}")

async def setup(bot):
    preferred_model_name = 'gemini-3-flash-preview'
    fallback_model_name = 'gemini-2.0-flash'
    model_to_use = None
    
    print("GeminiCog setup: Starting initialization with new google-genai SDK.")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("GeminiCog setup: Client initialized.")
        
        # Simple test to check model availability is harder in new SDK without listing, 
        # so we will default to the preferred model and let it fail gracefully if needed.
        # However, we can try to list models if we really want to check.
        # For now, let's just pick the preferred one.
        model_to_use = preferred_model_name
        
        await bot.add_cog(GeminiCog(bot, client, model_to_use))
        print(f"GeminiCog setup: Successfully loaded GeminiCog with model '{model_to_use}'.")

    except Exception as e:
        message = f"GeminiCog setup: An error occurred during initialization: {e}"
        print(message)
        await send_error_log(bot, message)
        raise
