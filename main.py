import os, time, requests, threading
import telebot
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return "OK - Bot is Live"

@bot.message_handler(commands=["start","help"])
def cmd_start(m):
    bot.reply_to(m, "Bot Live! Commands:\n/scan - scan\n/futures - futures\n/margin - margin")

@bot.message_handler(commands=["scan"])
def cmd_scan(m):
    bot.reply_to(m, "Scanning... this is test scan - code works!")
    # тут потом добавим логику Bitget

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
