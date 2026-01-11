import discord
from discord.ext import commands
from PIL import Image
import pytesseract
import io
import aiohttp
import logging
import os
import platform

# Set up logger
logger = logging.getLogger(__name__)

# Attempt to locate Tesseract on Windows if not in PATH
if platform.system() == "Windows":
    # Common default installation paths
    potential_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
    ]
    
    # Check if tesseract is already in PATH by trying to call it? 
    # Actually, pytesseract just checks the cmd variable.
    # Let's check if the default cmd 'tesseract' works later, 
    # but primarily set it if we find the binary and it's not set.
    
    found_tesseract = False
    for path in potential_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract executable found and set to: {path}")
            found_tesseract = True
            break
            
    if not found_tesseract:
        logger.warning("Tesseract executable not found in standard Windows paths. Ensure it is in your PATH.")

class OCR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ocr", description="Performs OCR on an attached image or URL to extract text.")
    async def ocr(self, ctx: commands.Context, image_url: str = None):
        target_url = None
        if ctx.message.attachments:
            target_url = ctx.message.attachments[0].url
        elif image_url:
            target_url = image_url
        else:
            await ctx.send("Please attach an image to the command message or provide a URL.")
            return

        async with ctx.typing():
            try:
                # Fetch image from URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(target_url) as resp:
                        if resp.status != 200:
                            await ctx.send(f"Could not download image. Status: {resp.status}")
                            return
                        image_bytes = await resp.read()

                # Process image with Tesseract
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    text = pytesseract.image_to_string(img)
                    
                    if not text.strip():
                        await ctx.send("No text detected in the image.")
                        return

                    # Format output (handling Discord's 2000 char limit)
                    formatted_text = f"**OCR Result:**\n```\n{text}\n```"
                    if len(formatted_text) > 2000:
                         # Split simple logic or just send first chunk
                         await ctx.send(formatted_text[:1990] + "\n```... (truncated)")
                    else:
                        await ctx.send(formatted_text)

                except pytesseract.TesseractNotFoundError:
                    error_msg = (
                        "Tesseract OCR is not installed or not found in your PATH.\n"
                        "Please install Tesseract-OCR and restart the bot.\n"
                        "Windows: https://github.com/UB-Mannheim/tesseract/wiki"
                    )
                    await ctx.send(error_msg)
                    logger.error("Tesseract not found.")
                except Exception as e:
                    await ctx.send(f"An error occurred during OCR processing: {e}")
                    logger.error(f"OCR Error: {e}")

            except Exception as e:
                await ctx.send(f"Failed to process request: {e}")
                logger.error(f"OCR Request Error: {e}")

async def setup(bot):
    await bot.add_cog(OCR(bot))
