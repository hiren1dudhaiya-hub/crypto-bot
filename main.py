import os, asyncio, aiohttp, numpy as np
from collections import deque
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8465758405:AAH_YOUR_TOKEN_HERE"
CHAT_ID = int(os.getenv("CHAT_ID") or "7086505670")
BINANCE_API = "https://data-api.binance.vision"
sent_messages = deque(maxlen=10)

DELTA_COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","SHIBUSDT","PEPEUSDT","AVAXUSDT","ADAUSDT","LINKUSDT","DOTUSDT","TRXUSDT","BCHUSDT","LTCUSDT","NEARUSDT","SUIUSDT","APTUSDT","ARBUSDT","OPUSDT","POLUSDT","ETCUSDT","FILUSDT","UNIUSDT","AAVEUSDT","ATOMUSDT","INJUSDT","TIAUSDT","SEIUSDT","JUPUSDT","BONKUSDT","WIFUSDT","FLOKIUSDT","FETUSDT","RENDERUSDT","ARUSDT","STXUSDT","MKRUSDT","LDOUSDT","ENAUSDT","STRKUSDT","BLURUSDT","JTOUSDT","BRETTUSDT","MEMEUSDT","ONDOUSDT"]

def calc_rsi(closes, period=9):
    deltas = np.diff(closes)
    seed = deltas[:period+1]
    up = seed[seed>=0].sum()/period
    down = -seed[seed<0].sum()/period
    if down == 0: down = 0.001
    rsi = np.zeros_like(closes)
    rsi[:period] = 100. - 100./(1.+up/down)
    for i in range(period, len(closes)-1):
        delta = deltas[i]
        upval = delta if delta>0 else 0.
        downval = -delta if delta<0 else 0.
        up = (up*(period-1)+upval)/period
        down = (down*(period-1)+downval)/period
        if down == 0: down = 0.001
        rsi[i+1] = 100. - 100./(1.+up/down)
    return rsi

async def get_data(session, symbol, sem):
    try:
        url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=30m&limit=120"
        async with sem:
            async with session.get(url, timeout=15) as r:
                kl30 = await r.json()
        if not isinstance(kl30, list) or len(kl30) < 60:
            return None

        closes90, highs90, lows90 = [], [], []
        for i in range(0, len(kl30)-2, 3):
            c1, c2, c3 = kl30[i], kl30[i+1], kl30[i+2]
            closes90.append(float(c3[4]))
            highs90.append(max(float(c1[2]), float(c2[2]), float(c3[2])))
            lows90.append(min(float(c1[3]), float(c2[3]), float(c3[3])))

        closes90 = np.array(closes90)
        highs90 = np.array(highs90)
        lows90 = np.array(lows90)
        if len(closes90) < 20:
            return None

        rsi9_s = calc_rsi(closes90, 9)
        rsi14_s = calc_rsi(closes90, 14)

        rsi9 = float(rsi9_s[-1])
        ma3 = float(np.mean(rsi9_s[-3:]))
        rsi14 = float(rsi14_s[-1])
        ma9 = float(np.mean(rsi14_s[-9:]))

        high_break = highs90[-1] > highs90[-2]
        low_break = lows90[-1] < lows90[-2]

        coin = symbol.replace("USDT","")
        # SHORT FORMAT - Telegram limit ke liye
        rsi_str = f"R9:{rsi9:.0f}>M3:{ma3:.0f} R14:{rsi14:.0f}>M9:{ma9:.0f}" if rsi9>ma3 else f"R9:{rsi9:.0f}<M3:{ma3:.0f} R14:{rsi14:.0f}<M9:{ma9:.0f}"

        if high_break and rsi9 > ma3 and rsi14 > ma9:
            return (coin, f"LONG | {rsi9:.0f}>{ma3:.0f} | HB", symbol, True)
        if low_break and rsi9 < ma3 and rsi14 < ma9:
            return (coin, f"SHORT | {rsi9:.0f}<{ma3:.0f} | LB", symbol, True)

        # Tight me sirf coin name - message chhota rahega
        return (coin, f"{'BULL' if rsi9>ma3 else 'BEAR'}", symbol, False)

    except Exception as e:
        print(f"Err {symbol}: {e}")
        return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(10)
        results = await asyncio.gather(*[get_data(session,s,sem) for s in DELTA_COINS])
        final = [r for r in results if r is not None]
        final.sort(key=lambda x: (0 if x[3] else 1, x[0]))
        return final

def format_msg(results):
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    time_str = ist.strftime("%I:%M %p - %d %b")
    signals = [r for r in results if r[3]]
    tight = [r for r in results if not r[3]]

    msg = f"<b>90m BREAK SCAN | {time_str}</b>\n"
    msg += f"<b>{len(results)} COINS | R9/M3 + R14/M9</b>\n\n"

    if signals:
        msg += "<b>SIGNALS:</b>\n"
        for coin,sig,sym in signals:
            link = f"https://www.delta.exchange/app/futures/trade/{coin}/{coin}USD"
            if "LONG" in sig:
                msg += f'🟩 <a href="{link}">{coin}</a> {sig}\n'
            else:
                msg += f'🟥 <a href="{link}">{coin}</a> {sig}\n'
        msg += "\n"
    
    # Tight list chhota - sirf 15 coin dikhao
    msg += f"<b>TIGHT ({len(tight)}):</b> "
    msg += ", ".join([f"{c}" for c,s,ss in tight[:20]])
    if len(tight) > 20:
        msg += f" +{len(tight)-20} more"
    
    msg += f"\n\n<i>Signals: {len(signals)}/{len(results)}</i>"
    return msg

async def delete_old_messages(bot):
    while len(sent_messages) > 2:
        old_id = sent_messages.popleft()
        try: await bot.delete_message(chat_id=CHAT_ID, message_id=old_id)
        except: pass

async def background_scan(chat_id, context):
    try:
        results = await do_scan()
        if not results:
            await context.bot.send_message(chat_id=chat_id, text="❌ Data fail - Retry /scan")
            return
        txt = format_msg(results)
        sent = await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        sent_messages.append(sent.message_id)
        await delete_old_messages(context.bot)
    except Exception as e:
        print(f"Scan Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {e}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("90m scan...")
    await background_scan(update.effective_chat.id, context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BOT ONLINE - 90m BREAK FINAL")

async def auto_loop(app):
    await asyncio.sleep(10)
    while True:
        try:
            await background_scan(CHAT_ID, app)
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Loop error: {e}")
            await asyncio.sleep(30)

def main():
    print("Starting FINAL 90m Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    async def on_startup(a):
        asyncio.create_task(auto_loop(a))
    app.post_init = on_startup
    app.run_polling()

if __name__ == "__main__":
    main()
