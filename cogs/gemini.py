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

    def _get_model_from_flags(self, flags: str) -> str:
        match = re.search(r"-m\s+([^\s]+)", flags)
        if match:
            return match.group(1)
        return self.model_name

    @commands.command(
        name="describe", 
        description="Describes an image using Gemini (defaults to gemini-3-flash-preview). Use -m to specify a model.", 
        usage="[-m model]",
        help="Describes an attached image. You can optionally specify which Gemini model to use by adding '-m model_name' to your message (e.g., `alii!describe -m gemini-3-flash-preview`)."
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

        target_model = self._get_model_from_flags(flags)

        async with ctx.typing():
            try:
                # Fetch image from URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status != 200:
                            await ctx.send("Could not download image from Discord. The error has been logged.")
                            await send_error_log(self.bot, f"Failed to download image from {attachment.url} with status {resp.status}")
                            return
                        image_bytes = await resp.read()

                # Prepare image for Gemini
                img = Image.open(io.BytesIO(image_bytes))

                # Send to Gemini
                # The new SDK uses client.models.generate_content
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=["Describe this image in detail for a blind user, focusing on the key objects, colors, and the overall scene.", img]
                )

                if response.text:
                    await utils.send_long_message(ctx, f"**Image Description ({target_model}):**\n{response.text}")
                else:
                    error_detail = "Gemini API returned no description."
                    await ctx.send(truncate_message(error_detail))
                    await send_error_log(self.bot, "Gemini API returned empty text.")

            except Exception as e:
                await ctx.send("An error occurred while describing the image. The error has been logged.")
                await send_error_log(self.bot, f"Exception during image description: {e}")
    
    @commands.command(
        name="test", 
        description="Tests connection to Gemini (defaults to gemini-3-flash-preview). Use -m to specify a model.", 
        usage="[-m model]",
        help="Tests if the bot can communicate with the Gemini API. You can optionally specify which model to test by adding '-m model_name' (e.g., `alii!test -m gemini-3-flash-preview`)."
    )
    async def test(self, ctx: commands.Context, *, flags: str = ""):
        if not self.client:
            await ctx.send("The Gemini client is not initialized.")
            return
            
        target_model = self._get_model_from_flags(flags)
            
        await ctx.send(f"Testing connection to Gemini API with model: `{target_model}`")
        try:
            response = self.client.models.generate_content(
                model=target_model,
                contents="This is a test. Is the API working?"
            )
            if response.text:
                await ctx.send("Successfully connected to the Gemini API and received a response.")
            else:
                await ctx.send("Connected, but received empty response.")
        except Exception as e:
            await ctx.send("Failed to connect to the Gemini API. The error has been logged.")
            await send_error_log(self.bot, f"Gemini API test failed: {e}")

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