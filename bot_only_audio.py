# import os
# import logging
# from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     MessageHandler,
#     ConversationHandler,
#     filters,
#     ContextTypes
# )
# import yt_dlp
# import asyncio

# # Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# # Define conversation states using integers
# GET_LINK, GET_FILENAME = range(2)

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Step 1: Welcome the user and ask for the YouTube link."""
#     await update.message.reply_text(
#         "🎵 Welcome to YouTube Audio Downloader\n\n"
#         "Convert your favorite YouTube videos into high-quality audio in just a few clicks.\n\n"
#         "🔗 Step 1: Paste the YouTube video URL below to get started.\n\n"
#         "⚡ Fast • 🎧 High Quality • 🚀 Easy to Use\n\n"
#         "👨‍💻 Developed by Hritik Koley",

#         parse_mode="Markdown"
#     )
#     return GET_LINK

# async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Step 2: Validate the link and ask for a custom filename."""
#     url = update.message.text.strip()
    
#     if not ("youtube.com" in url or "youtu.be" in url):
#         await update.message.reply_text("❌ That doesn't look like a valid YouTube link. Please try sending the link again:")
#         return GET_LINK  # Keep them in the GET_LINK state until they provide a valid one

#     # Save the URL in the user's conversation context memory
#     context.user_data['url'] = url

#     # Provide a quick reply keyboard option to skip custom naming
#     reply_keyboard = [['Use Video Title']]
    
#     await update.message.reply_text(
#         "✅ Link received!\n\n"
#         "➡️ **Step 2:** What would you like to name this audio track?\n"
#         "Type a custom name (e.g., My Favorite Song), or tap the button below to use the original YouTube title.",
#         reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
#         parse_mode="Markdown"
#     )
#     return GET_FILENAME

# async def receive_filename_and_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Step 3: Process everything, download in a thread, and send the embedded audio player."""
#     user_choice = update.message.text.strip()
#     url = context.user_data.get('url')
    
#     status_message = await update.message.reply_text(
#         "⚙️ **Step 3: Processing...**\nDownloading and converting your audio. Please wait...", 
#         reply_markup=ReplyKeyboardRemove(),
#         parse_mode="Markdown"
#     )

#     unique_id = update.message.message_id
#     output_template = f"audio_{unique_id}"
#     expected_file = f"{output_template}.mp3"

#     current_dir = os.path.dirname(os.path.abspath(__file__))
    
#     ydl_opts = {
#         'format': 'bestaudio/best',
#         'outtmpl': os.path.join(current_dir, output_template),
#         'quiet': True,
#         'ffmpeg_location': current_dir,
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '320',
#         }],
#         # Add a custom network timeout threshold within yt-dlp itself
#         'socket_timeout': 30,
#     }

#     # Define an inner function that contains the blocking download step
#     def blocking_download():
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             return ydl.extract_info(url, download=True)

#     try:
#         # CRUCIAL: Run the blocking download in a separate background thread!
#         # This prevents Python 3.14's event loop from freezing or timing out.
#         info = await asyncio.to_thread(blocking_download)
        
#         if user_choice == 'Use Video Title':
#             final_title = info.get('title', 'Downloaded Audio')
#         else:
#             final_title = user_choice

#         # Strip out potential bad characters for standard file safety
#         final_title = "".join([c for c in final_title if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

#         try:
#             await status_message.edit_text("📤 Uploading your embedded audio player to the chat...")
#         except Exception:
#             status_message = await update.message.reply_text("📤 Uploading your embedded audio player to the chat...")

#         local_file_path = os.path.join(current_dir, expected_file)
        
#         # Verify file actually exists before uploading
#         if os.path.exists(local_file_path):
#             with open(local_file_path, 'rb') as audio_file:
#                 await update.message.reply_audio(
#                     audio=audio_file,
#                     title=final_title,
#                     filename=f"{final_title}.mp3"
#                 )
#             try:
#                 await status_message.delete()
#             except Exception:
#                 pass
#             await update.message.reply_text("✨ Done! You can play it directly above. Send /start if you want to download another one!")
#         else:
#             raise FileNotFoundError("The audio file was not generated properly by the processor.")

#     except Exception as e:
#         logger.error(f"Error: {e}")
#         error_text = f"❌ Failed during extraction. Error: {str(e)[:100]}"
#         try:
#             await status_message.edit_text(error_text)
#         except Exception:
#             await update.message.reply_text(error_text)
        
#     finally:
#         local_file_path = os.path.join(current_dir, expected_file)
#         if os.path.exists(local_file_path):
#             os.remove(local_file_path)

#     context.user_data.clear()
#     return ConversationHandler.END

# async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Allows the user to cancel the step-by-step guidance mid-way."""
#     await update.message.reply_text(
#         "❌ Conversation cancelled. Send /start whenever you want to try again.", 
#         reply_markup=ReplyKeyboardRemove()
#     )
#     context.user_data.clear()
#     return ConversationHandler.END
# async def main_async() -> None:
#     """Start the bot asynchronously."""
#     if not TOKEN:
#         print("[Error] TELEGRAM_BOT_TOKEN variable not set!")
#         return

#     application = Application.builder().token(TOKEN).build()

#     # Set up the state machine step handler
#     conv_handler = ConversationHandler(
#         entry_points=[CommandHandler("start", start)],
#         states={
#             GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
#             GET_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filename_and_process)],
#         },
#         fallbacks=[CommandHandler("cancel", cancel)],
#     )

#     application.add_handler(conv_handler)

#     print("Step-by-step guided bot is booting up...")
    
#     # We use initialize/start/initialize polling loops explicitly inside the running asyncio block
#     await application.initialize()
#     await application.start()
#     await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
#     # Keep it running until interrupted
#     print("Bot is active! Press Ctrl+C in this terminal to stop.")
#     while True:
#         await asyncio.sleep(3600)

# if __name__ == '__main__':
#     try:
#         # This forcefully spins up a modern event loop that Python 3.14 demands
#         asyncio.run(main_async())
#     except (KeyboardInterrupt, SystemExit):
#         print("\nBot stopped cleanly.")