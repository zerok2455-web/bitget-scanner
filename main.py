import os, threading, time, requests, io, json, urllib.parse
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Live - No Build"

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

def make_candle_image(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 50)
    if len(candles) < 10:
        return None
    try:
        # данные для quickchart: [{o,h,l,c},...]
        data = []
        for c in candles[-40:]:
            o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4])
            data.append({"o":o,"h":h,"l":l,"c":cl})

        chart_config = {
            "type": "candlestick",
            "data": {
                "datasets": [{
                    "label": symbol,
                    "data": data,
                    "color": {"up": "#26a69a", "down": "#ef5350", "unchanged": "#888888"}
                }]
            },
            "options": {
                "title": {"display": True, "text": f"{symbol} {granularity} - Lucifer"},
                "backgroundColor": "#131722",
                "legend": {"labels": {"fontColor": "white"}},
            }
        }
        encoded = urllib.parse.quote(json.dumps(chart_config))
        url = f"https://quickchart.io/chart?c={encoded}&width=800&height=400&backgroundColor=%23131722&format=png"

        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            buf = io.BytesIO(r.content)
            buf.seek(0)
            return buf
        return None
    except Exception as e:
        print(f"chart error {e}")
        return None

def make_buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_c = types.InlineKeyboardButton("🕯️ Свечи красно/зеленые", callback_data=f"chart_{symbol}")
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
    bot.send_message(m.chat.id, f"🔍 Сканирую +{thresh}%...")
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
            bot.answer_callback_query(call.id, f"Рисую свечи {sym}...")
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_candle_image(sym,"1h")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"🕯️ {sym} 1H - зеленый рост / красный падение", reply_markup=make_buttons(sym))
            else:
                bot.send_message(call.message.chat.id, f"Не смог загрузить график {sym}")
        elif d.startswith("chart5m_"):
            sym=d.replace("chart5m_","")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_candle_image(sym,"5m")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"⏱️ {sym} 5м свечи", reply_markup=make_buttons(sym))
        elif d.startswith("refresh_"):
            sym=d.replace("refresh_","")
            bot.answer_callback_query(call.id)
            img=make_candle_image(sym,"1h")
            if img:
                bot.send_photo(call.message.chat.id, img, caption=f"🔄 {sym}", reply_markup=make_buttons(sym))
    except Exception as e:
        print(f"cb err {e}")

def run_bot():
    while True:
        try:
            print("Polling start")
            bot.infinity_polling(timeout=90, long_polling_timeout=60, none_stop=True)
        except Exception as e:
            print(f"poll err {e}")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port=int(os.environ.get("PORT",10000))
    app.run(host='0.0.0.0', port=port)
