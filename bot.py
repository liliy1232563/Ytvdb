# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | LISA-KOREA/YouTube-Video-Download-Bot

# [⚠️ Do not change this repo link ⚠️] :- https://github.com/LISA-KOREA/YouTube-Video-Download-Bot


import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyrogram import Client, filters
from Youtube.config import Config


# ==============================
# Render Health Check Server
# ==============================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🌐 Web server running on port {port}")
    server.serve_forever()


# Start Render web server
threading.Thread(target=start_web_server, daemon=True).start()


if __name__ == "__main__":

    # 🚨 SECURITY WARNING SECTION 🚨
    print("\n" + "=" * 60)
    print("🚨  SECURITY WARNING for Forked Users  🚨")
    print("-" * 60)
    print("⚠️  This is a PUBLIC repository.")
    print("🧠  Do NOT expose your BOT_TOKEN, API_ID, API_HASH, or cookies.txt.")
    print("💡  Always use Heroku Config Vars or a private .env file to store secrets.")
    print("🔒  Never commit sensitive data to your fork — anyone can steal it!")
    print("📢  Support: @NT_BOTS_SUPPORT")
    print("=" * 60 + "\n")


# Create a Pyrogram client
app = Client(
    "my_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="Youtube")
)


# Start the bot
print("🎊 I AM ALIVE 🎊")
app.run()