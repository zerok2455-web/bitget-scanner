for t in s:
            if t["symbol"].endswith("USDT"): spot[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    try:
        f=requests.get("https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",timeout=12).json()["data"]
        for t in f:
            if t["symbol"].endswith("USDT"): fut[t["symbol"]]=float(t.get("change24h",0))
    except: pass
    return spot, fut

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m,"💎 FULL BOT\n/scan - ВСЁ СРАЗУ\n/futures - фьючи с плечом\n/margin - маржа\n/signal BTCUSDT")

@bot.message_handler(commands=['scan'])
def scan(m):
    bot.reply_to(m,"⏳ Сканирую SPOT+FUTURES+MARGIN+LEVERAGE...")
    spot,fut=get_tickers()
    all_syms=set(list(spot.keys())+list(fut.keys()))
    combined=[]
    for sym in all_syms:
        cs=spot.get(sym,0); cf=fut.get(sym,0)
        if max(cs,cf)>3: combined.append((sym,cs,cf,max(cs,cf)))
    combined=sorted(combined,key=lambda x:x[3],reverse=True)[:5]
    for sym,cs,cf,_ in combined:
        a=analyze(sym,cs,cf,"futures" if cf>=cs else "spot")
        if not a: continue
        margin_icon="💰 МАРЖА 3x-10x" if a['is_margin'] else "Без маржи"
        text=f"""💎 {sym}
FUT {cf:.1f}% ({a['lev']} плечо) | SPOT {cs:.1f}%

{a['signal']} | {margin_icon}
Цена: {a['price']:.6f}

📍 ВХОД: {a['entry_low']:.6f} - {a['entry_high']:.6f}
🛑 СТОП: {a['stop']:.6f} (-{(1-a['stop']/a['price'])*100:.1f}%)
🎯 Т1: {a['tp1']:.6f} (+{(a['tp1']/a['price']-1)*100:.1f}%)
🎯 Т2: {a['tp2']:.6f}
🎯 Т3: {a['tp3']:.6f}

RSI {a['rsi']:.1f} | Объем x{a['vol_ratio']:.1f}
⚙️ Фьюч плечо: {a['lev']} | Маржа: {margin_icon}
Поддержка {a['support']:.6f} | Сопр {a['resistance']:.6f}
"""
        bot.send_message(m.chat.id
