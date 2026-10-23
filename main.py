import os, threading, time, requests, io
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "Lucifer Live"

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
        return list(reversed(r.get("data", [])))
    except:
        return []

def make_chart(symbol, granularity="1h"):
    candles = get_candles(symbol, granularity, 50)
    if len(candles) < 10:
        return None
    try:
        closes = []
        for c in candles[-40:]:
            closes.append(float(c[4]))
        
        is_up = closes[-1] >= closes[0]
        color = "#26a69a" if is_up else "#ef5350"
        
        cfg = {
            "type": "line",
            "data": {
                "labels": [str(i) for i in range(len(closes))],
                "datasets": [{
                    "label": symbol,
                    "data": closes,
                    "borderColor": color,
                    "backgroundColor": "rgba(0,0,0,0)",
                    "fill": False,
                    "pointRadius": 0,
                    "borderWidth": 3,
                    "tension": 0.1
                }]
            },
            "options": {
                "title": {"display": True, "text": f"{symbol} {granularity} {'GREEN' if is_up else 'RED'}", "fontColor": "white"},
                "legend": {"display": False},
                "scales": {
                    "xAxes": [{"ticks": {"display": False}, "gridLines": {"color": "#2a2e39"}}],
                    "yAxes": [{"ticks": {"fontColor": "white"}, "gridLines": {"color": "#2a2e39"}}]
                }
            }
        }
        
        resp = requests.post(
            "https://quickchart.io/chart",
            json={"chart": cfg, "width": 800, "height": 400, "backgroundColor": "#131722", "format": "png"},
            timeout=20
        )
        if resp.status_code == 200 and len(resp.content) > 1000:
            buf = io.BytesIO(resp.content)
            buf.seek(0)
            return buf
        return None
    except Exception as e:
        print(f"chart err {e}")
        return None

def make_buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("Sveci krasno/zeleno", callback_data=f"chart_{symbol}")
    b2 = types.InlineKeyboardButton("Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    b3 = types.InlineKeyboardButton("5m", callback_data=f"chart5m_{symbol}")
    b4 = types.InlineKeyboardButton(f"Refresh {symbol}", callback_data=f"refresh_{symbol}")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

@bot.message_handler(commands=['start','scan','scan2'])
def handle_scan(m):
    is_scan2 = "scan2" in m.text
    thresh = 2 if is_scan2 else 4
    bot.send_message(m.chat.id, f"Scan +{thresh}%...")
    tickers = get_spot_tickers()
    tickers = sorted(tickers, key=lambda x: float(x.get("change24h",0)), reverse=True)
    cnt=0
    for t in tickers:
        try:
            sym=t['symbol']
            if not sym.endswith("USDT"): continue
            ch=float(t.get("change24h",0))*100
            if ch<thresh or ch>40: continue
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
            bot.answer_callback_query(call.id, f"Chart {sym}")
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_chart(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"{sym} 1H", reply_markup=make_buttons(sym))
            else: bot.send_message(call.message.chat.id, f"Ne smog zagruzit grafik {sym}")
        elif d.startswith("chart5m_"):
            sym=d.replace("chart5m_","")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            img=make_chart(sym,"5m")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"{sym} 5m", reply_markup=make_buttons(sym))
        elif d.startswith("refresh_"):
            sym=d.replace("refresh_","")
            bot.answer_callback_query(call.id)
            img=make_chart(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"{sym}", reply_markup=make_buttons(sym))
    except Exception as e:
        print(f"cb {e}")

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
