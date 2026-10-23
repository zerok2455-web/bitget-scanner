import os
import threading
import time
import requests
import io
import json
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("BOT_TOKEN missing!")
    
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Live - Fixed Candles POST"

# --- API Bitget ---
def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code") == "00000" else []
    except Exception as e:
        print(f"tickers error {e}")
        return []

def get_candles(symbol, granularity="1h", limit=80):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        data = r.get("data", [])
        return list(reversed(data))
    except Exception as e:
        print(f"candles error {symbol}: {e}")
        return []

# --- CHART RED/GREEN FIXED POST ---
def make_candle_image(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 60)
    if len(candles) < 10:
        return None
    try:
        # 40 последних свечей для графика
        ohlc_data = []
        closes = []
        for i, c in enumerate(candles[-40:]):
            try:
                o = float(c[1])
                h = float(c[2])
                l = float(c[3])
                cl = float(c[4])
                ohlc_data.append({"x": i, "o": o, "h": h, "l": l, "c": cl})
                closes.append(cl)
            except:
                continue

        if
