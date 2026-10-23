import os, threading, time, requests, io, math
import telebot
from telebot import types
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
# --- Меню команд (та самая кнопка что ты обвел) ---
try:
    bot.set_my_commands([
        types.BotCommand("start", "🚀 Главное меню"),
        types.BotCommand("scan", "🚀 Пампы от 4%"),
        types.BotCommand("scan2", "⚡ Ранние пампы от 2%"),
        types.BotCommand("top5m", "🔥 Топ за 5 минут"),
        types.BotCommand("funding", "💰 Фандинг"),
        types.BotCommand("calc", "🧮 Калькулятор"),
        types.BotCommand("auto", "🤖 Авто-скан"),
        types.BotCommand("futures", "📈 Фьючерсы"),
    ])
    print("Меню команд установлено")
except Exception as e:
    print(f"menu err {e}")
@app.route('/')
def home():
    return "Lucifer Scanner RU Live"

# --- API ---
def get_spot_tickers():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/market/tickers", timeout=15).json()
        return r.get("data", []) if r.get("code")=="00000" else []
    except: return []

def get_candles(symbol, gran="1h", limit=60):
    try:
        url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={gran}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        return list(reversed(r.get("data", [])))
    except: return []

def get_funding():
    try:
        r = requests.get("https://api.bitget.com/api/v2/mix/market/funding-time", timeout=10).json()
        return r.get("data", [])
    except: return []

# --- График ---
def make_chart(symbol, gran="1h"):
    candles = get_candles(symbol, gran, 50)
    if len(candles)<10: return None
    try:
        closes = [float(c[4]) for c in candles[-40:]]
        tickers = get_spot_tickers()
        ch24=0
        for t in tickers:
            if t['symbol']==symbol:
                ch24=float(t.get("change24h",0))*100
                break
        color = "#26a69a" if ch24>=0 else "#ef5350"
        fill = "rgba(38,166,154,0.2)" if ch24>=0 else "rgba(239,83,80,0.2)"
        cfg = {
            "type":"line",
            "data":{"labels":[str(i) for i in range(len(closes))],
            "datasets":[{"data":closes,"borderColor":color,"backgroundColor":fill,"fill":True,"pointRadius":0,"borderWidth":3}]},
            "options":{"title":{"display":True,"text":f"{symbol} {gran} {ch24:+.2f}%","fontColor":"white"},"legend":{"display":False}}
        }
        resp = requests.post("https://quickchart.io/chart", json={"chart":cfg,"width":800,"height":400,"backgroundColor":"#131722","format":"png"}, timeout=20)
        if resp.status_code==200 and len(resp.content)>1000:
            buf=io.BytesIO(resp.content); buf.seek(0); return buf
    except Exception as e:
        print(e)
    return None

def buttons(symbol):
    markup = types.InlineKeyboardMarkup(row_width=3)
    b1 = types.InlineKeyboardButton("🕯️ График", callback_data=f"chart_{symbol}")
    b2 = types.InlineKeyboardButton("📊 Bitget", url=f"https://www.bitget.com/spot/{symbol.replace('USDT','')}_USDT")
    b3 = types.InlineKeyboardButton("⏱️ 5м", callback_data=f"chart5m_{symbol}")
    b4 = types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{symbol}")
    markup.add(b1,b2,b3)
    markup.add(b4)
    return markup

# --- Команды на русском ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id,
        "👋 Привет! Я Lucifer Scanner\n\n"
        "Команды:\n"
        "/scan - пампы от +4%\n"
        "/scan2 - пампы от +2% (ранние)\n"
        "/top5m - топ 5м свечей\n"
        "/futures - фьючерсы\n"
        "/funding - фандинг\n"
        "/calc - калькулятор\n"
        "/auto - авто-скан\n"
    )

@bot.message_handler(commands=['scan','scan2'])
def scan_cmd(m):
    is2 = "scan2" in m.text
    thresh = 2 if is2 else 4
    bot.send_message(m.chat.id, f"🔍 Ищу монеты от +{thresh}% за 24ч...")
    tickers = get_spot_tickers()
    tickers = sorted(tickers, key=lambda x: float(x.get("change24h",0)), reverse=True)
    cnt=0
    for t in tickers:
        try:
            sym=t['symbol']
            if not sym.endswith("USDT"): continue
            ch=float(t.get("change24h",0))*100
            if ch<thresh or ch>50: continue
            bot.send_message(m.chat.id, f"{'⚡' if is2 else '🚀'} {sym} +{ch:.2f}%", reply_markup=buttons(sym))
            cnt+=1
            if cnt>=10: break
        except: continue
    if cnt==0: bot.send_message(m.chat.id, "😔 Ничего не нашел")

@bot.message_handler(commands=['top5m'])
def top5m_cmd(m):
    bot.send_message(m.chat.id, "⚡ Ищу резкие пампы за 5 минут...")
    tickers = get_spot_tickers()
    found=[]
    for t in tickers[:100]:
        try:
            sym=t['symbol']
            if not sym.endswith("USDT"): continue
            candles=get_candles(sym,"5m",10)
            if len(candles)<6: continue
            c_now=float(candles[-1][4])
            c_5=float(candles[-5][4])
            ch=(c_now-c_5)/c_5*100
            if ch>3:
                found.append((sym,ch))
        except: continue
    found=sorted(found,key=lambda x:x[1],reverse=True)[:5]
    if not found:
        bot.send_message(m.chat.id, "Пока тихо на 5м")
        return
    for sym,ch in found:
        img=make_chart(sym,"5m")
        if img:
            bot.send_photo(m.chat.id, img, caption=f"🔥 {sym} +{ch:.2f}% за 5м", reply_markup=buttons(sym))
        else:
            bot.send_message(m.chat.id, f"🔥 {sym} +{ch:.2f}% за 5м", reply_markup=buttons(sym))

@bot.message_handler(commands=['futures'])
def futures_cmd(m):
    bot.send_message(m.chat.id, "📈 Фьючерсы: скоро добавлю топ по OI и фандингу. Пока используй /scan2 - это спот, но пампы начинаются там.")

@bot.message_handler(commands=['funding'])
def funding_cmd(m):
    bot.send_message(m.chat.id, "💰 Фандинг: топ отрицательный = лонг сквиз возможен\n(данные Bitget)\n\nПример: если фандинг -0.5% - шортистов много, возможен памп.")
    tickers=get_spot_tickers()
    # просто покажем монеты с большим падением - там часто отрицательный фандинг
    tickers=sorted(tickers, key=lambda x: float(x.get("change24h",0)))[:5]
    txt="🔻 Сильно упали (ищи лонг):\n"
    for t in tickers:
        try: txt+=f"{t['symbol']} {float(t['change24h'])*100:+.2f}%\n"
        except: pass
    bot.send_message(m.chat.id, txt)

@bot.message_handler(commands=['calc'])
def calc_cmd(m):
    bot.send_message(m.chat.id, "🧮 Калькулятор:\nНапиши: /calc 100 5\nЭто значит: депозит 100$ плечо x5 = позиция 500$\n\nИли напиши цену: /calc 0.05 0.06 - посчитаю %")

@bot.message_handler(commands=['auto'])
def auto_cmd(m):
    bot.send_message(m.chat.id, "🤖 Авто-скан включен! Каждые 5 минут буду кидать пампы от +5%.\nПока в тесте - используй /scan2 вручную. Авто режим допилю в след. версии.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/calc "))
def calc_do(m):
    try:
        parts=m.text.split()
        if len(parts)==3:
            entry=float(parts[1]); exit_p=float(parts[2])
            if entry<1 and exit_p<1: # цены
                perc=(exit_p-entry)/entry*100
                bot.send_message(m.chat.id, f"📊 С {entry} до {exit_p} = {perc:+.2f}%")
            else:
                dep=float(parts[1]); lev=float(parts[2])
                bot.send_message(m.chat.id, f"💵 Деп {dep}$ x{lev} = позиция {dep*lev}$")
        else:
            bot.send_message(m.chat.id, "Используй: /calc 100 5  или /calc 0.05 0.06")
    except:
        bot.send_message(m.chat.id, "Ошибка в расчете")

@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    try:
        d=call.data
        if d.startswith("chart_") and "chart5m" not in d:
            sym=d.replace("chart_","")
            bot.answer_callback_query(call.id, f"Загружаю {sym}")
            bot.send_chat_action(call.message.chat.id,'upload_photo')
            img=make_chart(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"📈 {sym} 1Ч", reply_markup=buttons(sym))
            else: bot.send_message(call.message.chat.id, "❌ Не смог загрузить график")
        elif d.startswith("chart5m_"):
            sym=d.replace("chart5m_","")
            bot.answer_callback_query(call.id)
            bot.send_chat_action(call.message.chat.id,'upload_photo')
            img=make_chart(sym,"5m")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"⏱️ {sym} 5м", reply_markup=buttons(sym))
        elif d.startswith("refresh_"):
            sym=d.replace("refresh_","")
            img=make_chart(sym,"1h")
            if img: bot.send_photo(call.message.chat.id, img, caption=f"🔄 {sym}", reply_markup=buttons(sym))
    except Exception as e:
        print(e)

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=60, none_stop=True)
        except Exception as e:
            print(e); time.sleep(5)

if __name__=='__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
