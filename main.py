import telebot, requests, os
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
def get_tickers():
    try:
        r=requests.get("https://api.bitget.com/api/v2/spot/market/tickers",timeout=10).json()
        return r.get("data",[]) if r.get("code")=="00000" else []
    except: return []
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "✅ Бот 24/7 работает!\n/scan - пампы\n/price BTC")
@bot.message_handler(commands=['scan'])
def scan(m):
    tickers=get_tickers()
    pumps=[]
    for t in tickers:
        s=t.get("symbol","")
        if not s.endswith("USDT"): continue
        try:
            vol=float(t.get("quoteVolume",0))
            if vol<50000: continue
            ch=float(t.get("changeUtc24h",0))*100
            if 5<=ch<=90:
                pumps.append((s,ch,t.get("lastPr")))
        except: continue
    pumps.sort(key=lambda x:x[1],reverse=True)
    if not pumps:
        bot.send_message(m.chat.id,"Пампов нет 😴")
        return
    msg="🔥 Пампы Bitget:\n\n"
    for s,c,p in pumps[:15]:
        msg+=f"{s} +{c:.1f}% — {p}\n"
    bot.send_message(m.chat.id,msg)
@bot.message_handler(commands=['price'])
def price(m):
    try:
        coin=m.text.split()[1].upper()
        if not coin.endswith("USDT"): coin+="USDT"
        r=requests.get(f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={coin}",timeout=5).json()
        t=r["data"][0]
        bot.send_message(m.chat.id,f"{coin}: {t['lastPr']}$ ({float(t['changeUtc24h'])*100:+.1f}%)")
    except:
        bot.send_message(m.chat.id,"Пиши: /price BTC")
bot.infinity_polling()
