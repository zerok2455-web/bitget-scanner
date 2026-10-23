import os, threading, time, requests, io
import telebot
from telebot import types
from flask import Flask
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Live - PIL Candles"

def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except:
        return []

def get_candles(symbol, granularity="1h", limit=60):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        data = r.get("data", [])
        return list(reversed(data))
    except:
        return []

def make_candle_image_pil(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 60)
    if len(candles) < 20:
        return None
    try:
        opens = [float(c[1]) for c in candles][-50:]
        highs = [float(c[2]) for c in candles][-50:]
        lows = [float(c[3]) for c in candles][-50:]
        closes = [float(c[4]) for c in candles][-50:]
    except:
        return None

    W, H = 1000, 400
    pad = 40
    img = Image.new('RGB', (W, H), '#131722')
    draw = ImageDraw.Draw(img)

    min_price = min(lows)
    max_price = max(highs)
    price_range = max_price - min_price
    if price_range == 0:
        price_range = 1

    def y_of(price):
        return H - pad - (price - min_price) / price_range * (H - pad*2)

    # grid
    for i in range(4):
        y = pad + i * (H - pad*2)//4
        draw.line([(pad, y), (W-10, y)], fill='#2a2e39', width=1)

    candle_w = (W - pad - 20) // len(closes)
    candle_body = max(2, candle_w - 2)

    for i in range(len(closes)):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        x = pad + i * candle_w + candle_w//2
        color = '#26a69a' if c >= o else '#ef5350'

        # wick
        draw.line([(x, y_of(l)), (x, y_of(h))], fill=color, width=1)
        # body
        top = y_of(max(o,c))
        bot_y = y_of(min(o,c))
        bh = max(2, bot_y - top)
        draw.rectangle([x-candle_body//2, top, x+candle_body//2, top+bh], fill=color, outline=color)

    # title
    try:
        draw.text((pad, 8), f"{symbol} {granularity} - Lucifer", fill='white')
        draw.text((pad, H-18), f"Low {min_price:.4f} | High {max_price:.4f}", fill='#888888')
    except:
        pass

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def make_buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_c = types.InlineKeyboardButton("🕯️ Свечи", callback_data=f"chart_{symbol}")
    btn_b = types.InlineKeyboardButton("🟢 Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    btn_5 = types.InlineKeyboardButton("⏱️ 5м", callback_data=f"chart5m_{symbol}")
    btn_r = types.InlineKeyboardButton(f"🔄 {symbol}", callback_data=f"refresh_{symbol}")
    markup.add(btn_c, btn_b)
    markup.add(btn_5, btn_r)
    return markup

@bot.message_handler(commands=['start','scan','scan2'])
def handle_scan(m):
    is_scan2 = "scan2" in m.text
    thresh = 2 if is_scan2 else 4
    bot.send_message(m.chat.id, f"🔍 +{thresh}%")
    tickers = get_spot_tickers()
    tickers = sorted(tickers, key=lambda x: float(x.get("change24h",0)), reverse=True)
    cnt=0
    for t in tickers:
        try:
            sym=t['symbol']
            if not sym.endswith("USDT"): continue
            ch=float(t.get("change24h",0))*100
            if ch<thresh or ch>30: continue
            bot.send_message(m.chat.id, f"{'⚡' if is_scan2 else '🚀'} {sym} +{ch:.2f}%", reply_markup=make_buttons(sym))
            cnt+=1
            if cnt>=10: break
        except: continue

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    try:
        d=call.data
        if d.startswith("chart_") and "chart5m" not in d:
            sym=d.replace("chart_","")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_candle_image_pil(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"🕯️ {sym} 1H", reply_markup=make_buttons(sym))
        elif d.startswith("chart5m_"):
            sym=d.replace("chart5m_","")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_candle_image_pil(sym,"5m")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"⏱️ {sym} 5м", reply_markup=make_buttons(sym))
        elif d.startswith("refresh_"):
            sym=d.replace("refresh_","")
            bot.answer_callback_query(call.id)
            img=make_candle_image_pil(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"🔄 {sym}", reply_markup=make_buttons(sym))
    except Exception as e:
        print(f"cb error {e}")

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=60, none_stop=True)
        except Exception as e:
            print(f"poll {e}")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port=int(os.environ.get("PORT",10000))
    app.run(host='0.0.0.0', port=port)
