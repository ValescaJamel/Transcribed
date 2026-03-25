import os
import socket
import asyncio
import tempfile

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from groq import Groq

# =========================
# 🔧 FIX 1: Force IPv4 (HuggingFace fix)
# =========================
def force_ipv4():
    orig_getaddrinfo = socket.getaddrinfo

    def new_getaddrinfo(*args, **kwargs):
        return [res for res in orig_getaddrinfo(*args, **kwargs) if res[0] == socket.AF_INET]

    socket.getaddrinfo = new_getaddrinfo

force_ipv4()

# =========================
# 🔐 Load ENV variables
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GROQ_API_KEY")

# =========================
# 🤖 Init Groq
# =========================
client = Groq(api_key=GROQ_API_KEY)

# =========================
# 🎤 Handle Voice / Audio
# =========================
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_message = await update.message.reply_text("⚡ Processing audio...")

    temp_audio_path = None

    try:
        audio_obj = update.message.voice or update.message.audio

        if not audio_obj:
            await status_message.edit_text("❌ No audio found.")
            return

        # Download file
        file = await context.bot.get_file(audio_obj.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            await file.download_to_drive(temp_audio_path)

        # Send to Groq
        with open(temp_audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(temp_audio_path, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )

        # Reply result
        await status_message.edit_text(
            f"📝 **Transcription:**\n\n{transcription}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_message.edit_text(f"❌ Error:\n{str(e)}")

    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# =========================
# 🚀 Main Runner (stable for HF)
# =========================
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO, handle_voice)
    )

    print("✅ Bot is running...")

    await app.initialize()
    await app.start()

    # Start polling manually (more stable on HF)
    await app.bot.initialize()
    await app.updater.start_polling()

    # Keep alive forever
    while True:
        await asyncio.sleep(3600)

# =========================
# ▶️ Entry point
# =========================
if __name__ == "__main__":
    asyncio.run(main())
