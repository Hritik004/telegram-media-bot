import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
import yt_dlp

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
YTDLP_AUTH_OPTS = {
    'cookiefile': COOKIES_FILE,
    'extractor_args': {
        'youtube': {
            'player_client': ['web'],
            'skip_unavailable_fragments': [True],
        }
    },
}

# Conversation States
GET_LINK, CHOOSE_TYPE, CHOOSE_QUALITY, CHOOSE_NAMING, GET_CUSTOM_NAME = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1: Welcome the user and prompt for a YouTube link."""
    await update.message.reply_text(
        "⬇️ *Advanced Media Downloader*\n"
        "_Developed by Hritik Koley_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔗 *Step 1 of 3* — Send your YouTube link\n\n"
        "_Paste the URL of the video, Short, or playlist you'd like to download\\._",
        parse_mode="MarkdownV2",
    )
    return GET_LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: Validate link and ask whether they want Audio or Video using inline buttons."""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("❌ Invalid link. Please send a valid YouTube link:")
        return GET_LINK

    context.user_data['url'] = url

    # Setup inline choice buttons for Audio vs Video
    keyboard = [
        [
            InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="type_audio"),
            InlineKeyboardButton("🎬 Video (MP4)", callback_data="type_video")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ Link received!\n\n"
        "➡️ **Step 2:** What would you like to extract?",
        reply_markup=reply_markup
    )
    return CHOOSE_TYPE

async def handle_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Branching Step: Handles the user clicking Audio or Video buttons."""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    context.user_data['download_type'] = choice

    if choice == "type_audio":
        await query.edit_message_text("⚡ Selected: **Audio Only**.\nInitializing size verification...", parse_mode="Markdown")
        return await run_size_and_naming_check(query.message, context, quality_format=None)
        
    elif choice == "type_video":
        keyboard = [
            [InlineKeyboardButton("⭐ Best Available", callback_data="quality_best")],
            [InlineKeyboardButton("🖥️ 2K Max (<=1440p)", callback_data="quality_1440")],
            [InlineKeyboardButton("📺 Full HD Max (<=1080p)", callback_data="quality_1080")],
            [InlineKeyboardButton("📱 HD Max (<=720p)", callback_data="quality_720")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➡️ **Step 3:** Choose your preferred maximum video quality resolution:",
            reply_markup=reply_markup
        )
        return CHOOSE_QUALITY

async def handle_quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the quality option click for videos and routes to download."""
    query = update.callback_query
    await query.answer()
    
    quality_choice = query.data
    context.user_data['quality_format'] = quality_choice
    await query.edit_message_text("⚡ Quality selected. Initializing size verification...")
    
    return await run_size_and_naming_check(query.message, context, quality_format=quality_choice)


async def run_size_and_naming_check(message, context: ContextTypes.DEFAULT_TYPE, quality_format) -> int:
    """Intermediate Step: Inspects metadata sizes. If valid, asks for naming preferences."""
    url = context.user_data.get('url')
    download_type = context.user_data.get('download_type')
    
    def check_metadata():
        format_str = "bestvideo+bestaudio/best"
        if download_type == "type_audio":
            format_str = "bestaudio/best"
        elif quality_format:
            quality_map = {
                "quality_best": "bestvideo+bestaudio/best",
                "quality_1440": "bestvideo[height<=1440]+bestaudio/best",
                "quality_1080": "bestvideo[height<=1080]+bestaudio/best",
                "quality_720": "bestvideo[height<=720]+bestaudio/best"
            }
            format_str = quality_map.get(quality_format, "bestvideo[height<=1080]+bestaudio/best")

        meta_opts = {'quiet': True, 'format': format_str, **YTDLP_AUTH_OPTS}
        with yt_dlp.YoutubeDL(meta_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.to_thread(check_metadata)
        video_title = info.get('title', 'Downloaded_Media')
        
        # Keep spaces and alphanumeric strings clean
        clean_title = "".join([c for c in video_title if c.isalnum() or c in ' .-_()']).strip()
        if not clean_title:
            clean_title = "Media_File"
        
        context.user_data['default_title'] = clean_title
        context.user_data['final_title'] = clean_title 

        estimated_bytes = 0
        if 'filesize_approx' in info and info['filesize_approx']:
            estimated_bytes = info['filesize_approx']
        elif 'filesize' in info and info['filesize']:
            estimated_bytes = info['filesize']
        elif 'requested_formats' in info:
            for f in info['requested_formats']:
                estimated_bytes += f.get('filesize', f.get('filesize_approx', 0)) or 0

        estimated_mb = estimated_bytes / (1024 * 1024)

        if estimated_mb >= 50.0:
            await message.reply_text(
                f"⚠️ **File is too large to send!**\n\n"
                f"The estimated media size is **{estimated_mb:.2f} MB**, but Telegram limits standard bots to a maximum upload size of **50.00 MB**.\n\n"
                f"🛑 *Download aborted:* Saved system bandwidth. Please use `/start` again and pick a lower quality resolution to stay under the limit!",
                parse_mode="Markdown"
            )
            context.user_data.clear()
            return ConversationHandler.END

        # Naming selection menu
        keyboard = [
            [InlineKeyboardButton(f"📄 Keep Default: {clean_title[:25]}...", callback_data="name_default")],
            [InlineKeyboardButton("✍️ Write Custom Name", callback_data="name_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            f"✅ **Size Verified!** ({estimated_mb:.2f} MB is safe)\n\n"
            f"➡️ **Step 4:** How would you like to name the saved file output?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return CHOOSE_NAMING

    except Exception as e:
        logger.error(f"Metadata Error: {e}")
        await message.reply_text(f"❌ Failed analyzing URL. Error: {str(e)[:100]}")
        context.user_data.clear()
        return ConversationHandler.END


async def handle_naming_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles naming choice button responses."""
    query = update.callback_query
    await query.answer()
    
    choice = query.data

    if choice == "name_default":
        await query.edit_message_text("⚡ Using default YouTube title. Starting download processing queue...")
        return await process_and_download(query.message, context)
        
    elif choice == "name_custom":
        await query.edit_message_text("✍️ Please type and send the **custom filename** you want to use:")
        return GET_CUSTOM_NAME


async def receive_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives custom text string from user chat input and sanitizes it."""
    custom_input = update.message.text.strip()
    
    clean_custom = "".join([c for c in custom_input if c.isalnum() or c in ' .-_()']).strip()
    
    if not clean_custom:
        clean_custom = "Custom_Media"

    context.user_data['final_title'] = clean_custom
    await update.message.reply_text(f"📝 Title set to: **{clean_custom}**\nStarting download processing queue...", parse_mode="Markdown")
    
    return await process_and_download(update.message, context)


async def process_and_download(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 5: Downloads the media asset, and renames the physical disk file to ensure custom titles match."""
    url = context.user_data.get('url')
    download_type = context.user_data.get('download_type')
    quality_format = context.user_data.get('quality_format')
    final_title = context.user_data.get('final_title', 'Downloaded_Media')
    
    status_message = await message.reply_text("📥 Downloading asset streams from YouTube server network...")

    unique_id = message.message_id
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    ydl_opts = {
        'quiet': True,
        'ffmpeg_location': current_dir,
        'socket_timeout': 30,
        **YTDLP_AUTH_OPTS,
    }


    # Temporary unique keys used to prevent download overlap crashes
    if download_type == "type_audio":
        temp_name = f"temp_audio_{unique_id}"
        expected_file = f"{temp_name}.mp3"
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(current_dir, temp_name),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        })
    else:
        temp_name = f"temp_video_{unique_id}"
        expected_file = f"{temp_name}.mp4"
        
        quality_map = {
            "quality_best": "bestvideo+bestaudio/best",
            "quality_1440": "bestvideo[height<=1440]+bestaudio/best",
            "quality_1080": "bestvideo[height<=1080]+bestaudio/best",
            "quality_720": "bestvideo[height<=720]+bestaudio/best"
        }
        
        ydl_opts.update({
            'format': quality_map.get(quality_format, "bestvideo[height<=1080]+bestaudio/best"),
            'outtmpl': os.path.join(current_dir, temp_name),
            'merge_output_format': 'mp4'
        })

    def blocking_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    # Variables for ultimate path garbage-cleanup tracking
    initial_temp_path = os.path.join(current_dir, expected_file)
    final_rename_path = None

    try:
        await asyncio.to_thread(blocking_download)
        
        if os.path.exists(initial_temp_path):
            # --- THE PHYSICAL FILE RENAME FIX MATRIX ---
            extension = ".mp3" if download_type == "type_audio" else ".mp4"
            final_filename = f"{final_title}{extension}"
            final_rename_path = os.path.join(current_dir, final_filename)

            # Safeguard: if target file already exists, clear it out first
            if os.path.exists(final_rename_path):
                os.remove(final_rename_path)
                
            os.rename(initial_temp_path, final_rename_path)
            # --------------------------------------------

            await status_message.edit_text("📤 Uploading media payload directly to chat player...")

            with open(final_rename_path, 'rb') as media_file:
                if download_type == "type_audio":
                    await message.reply_audio(
                        audio=media_file,
                        title=final_title,
                        filename=final_filename,
                        read_timeout=60,
                        write_timeout=120
                    )
                else:
                    await message.reply_video(
                        video=media_file,
                        supports_streaming=True,
                        filename=final_filename,
                        read_timeout=60,
                        write_timeout=120
                    )
            
            await status_message.delete()
            await message.reply_text("✨ Done! Use /start to download another media track.")
        else:
            raise FileNotFoundError("Muxed asset payload was not compiled successfully.")

    except Exception as e:
        logger.error(f"Error: {e}")
        error_text = f"❌ Failed during processing. Error: {str(e)[:100]}"
        await status_message.edit_text(error_text)
        
    finally:
        # File destruction routine for directory sanitation
        if os.path.exists(initial_temp_path):
            os.remove(initial_temp_path)
        if final_rename_path and os.path.exists(final_rename_path):
            os.remove(final_rename_path)

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aborts conversation."""
    await update.message.reply_text("❌ Action cancelled. Send /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END

async def main_async() -> None:
    if not TOKEN:
        print("[Error] TELEGRAM_BOT_TOKEN variable not set!")
        return

    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(120.0)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
            CHOOSE_TYPE: [CallbackQueryHandler(handle_type_choice, pattern="^type_")],
            CHOOSE_QUALITY: [CallbackQueryHandler(handle_quality_choice, pattern="^quality_")],
            CHOOSE_NAMING: [CallbackQueryHandler(handle_naming_choice, pattern="^name_")],
            GET_CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    application.add_handler(conv_handler)

    print("Step-by-step guided bot is booting up...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    print("Bot is active! Press Ctrl+C in this terminal to stop.")
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot stopped cleanly.")