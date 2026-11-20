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

def sma(arr, period):
    return np.mean(arr[-period:])

async def get_data(session, symbol, sem):
    try:
        # --- 12H DATA ---
        url12 = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=12h&limit=100"
        # --- 1H DATA FOR 9H BUILD ---
        url1h = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=200"
        async with sem:
            async with session.get(url12, timeout=10) as r12:
                kl12 = await r12.json()
            async with session.get(url1h, timeout=10) as r1h:
                kl1h = await r1h.json()

        if not isinstance(kl12, list) or len(kl12) < 30: return None
        if not isinstance(kl1h, list) or len(kl1h) < 90: return None

        closes12 = np.array([float(k[4]) for k in kl12])
        highs12 = np.array([float(k[2]) for k in kl12])
        lows12 = np.array([float(k[3]) for k in kl12])

        # BUILD 9H CANDLES FROM 1H (9 x 1H = 1 candle)
        closes9, highs9, lows9 = [], [], []
        for i in range(0, len(kl1h)-8, 9):
            chunk = kl1h[i:i+9]
            closes9.append(float(chunk[-1][4]))
            highs9.append(max(float(c[2]) for c in chunk))
            lows9.append(min(float(c[3]) for c in chunk))
        closes9 = np.array(closes9)
        highs9 = np.array(highs9)
        lows9 = np.array(lows9)

        if len(closes9) < 20: return None

        # --- INDICATORS ---
        rsi9_12 = calc_rsi(closes12, 9)[-1]
        ma3_12 = sma(closes12, 3)
        rsi14_9 = calc_rsi(closes9, 14)[-1]
        ma9_9 = sma(closes9, 9)

        # --- BREAKUP / BREAKDOWN ---
        # 12H Break
        high_break_12 = highs12[-1] > highs12[-2]
        low_break_12 = lows12[-1] < lows12[-2]
        # 9H Break
        high_break_9 = highs9[-1] > highs9[-2]
        low_break_9 = lows9[-1] < lows9[-2]

        coin = symbol.replace("USDT","")
        rsi_str = f"R9:{rsi9_12:.0f} M3:{ma3_12:.0f} | R14:{rsi14_9:.0f} M9:{ma9_9:.0f}"

        # --- NEW STRATEGY: 12H & 9H BREAKUP/BREAKDOWN ---
        is_bull_12 = rsi9_12 > ma3_12
        is_bull_9 = rsi14_9 > ma9_9
        is_bear_12 = rsi9_12 < ma3_12
        is_bear_9 = rsi14_9 < ma9_9

        # LONG CONDITION: Dono BULL + Koi ek me HIGH BREAK
        if is_bull_12 and is_bull_9 and (high_break_12 or high_break_9):
            brk = "12H-HIGH" if high_break_12 else "9H-HIGH" if high_break_9 else "HIGH"
            if high_break_12 and high_break_9: brk = "12H+9H HIGH BREAK"
            return (coin, f"LONG | {rsi_str} | {brk} ↑", symbol, True)
        
        # SHORT CONDITION: Dono BEAR + Koi ek me LOW BREAK
        if is_bear_12 and is_bear_9 and (low_break_12 or low_break_9):
            brk = "12H-LOW" if low_break_12 else "9H-LOW" if low_break_9 else "LOW"
            if low_break_12 and low_break_9: brk = "12H+9H LOW BREAK"
            return (coin, f"SHORT | {rsi_str} | {brk} ↓", symbol, True)

        # TIGHT / WAIT
        bull_count = (1 if is_bull_12 else 0) + (1 if is_bull_9 else 0)
        if bull_count == 2:
            status = "BULL Tight"
        elif bull_count == 0:
            status = "BEAR Tight"
        else:
            status = "MIX Tight"

        # Break info for tight
        if high_break_12 or high_break_9:
            status += " HighTry"
        if low_break_12 or low_break_9:
            status += " LowTry"

        sig = f"{status} | {rsi_str}"
        return (coin, sig, symbol, False)

    except Exception as e:
        # print(f"Error {symbol}: {e}")
        return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(10)
        results = await asyncio.gather(*[get_data(session,s,sem) for s in DELTA_COINS])
        final = [r for r in results if r is not None]; final.sort(key=lambda x: (0 if x[3] else 1, x[0])); return final

def format_msg(results):
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    time_str = ist.strftime("%I:%M %p IST - %d %b")
    signals = []; tight_list = []
    for coin,sig,symbol,is_sig in results:
        if is_sig: signals.append((coin,sig,symbol))
        else: tight_list.append((coin,sig,symbol))
    msg = f"<b>AUTO 5 MIN - {len(results)} COINS | {time_str}</b>\n"
    msg += "<b>12H R9/M3 + 9H R14/M9 | BREAKUP/DOWN</b>\n\n"
    for coin,sig,symbol in signals:
        link = f"https://www.delta.exchange/app/futures/trade/{coin}/{coin}USD"
        if "LONG" in sig:
            sig2 = sig.replace("LONG", "<b>LONG</b>").replace("HIGH", "<b>HIGH BREAK</b>")
            msg += f'🟩 <a href="{link}">{coin}</a> {sig2}\n'
        else:
            sig2 = sig.replace("SHORT", "<b>SHORT</b>").replace("LOW", "<b>LOW BREAK</b>")
            msg += f'🟥 <a href="{link}">{coin}</a> {sig2}\n'
    for coin,sig,symbol in tight_list:
        link = f"https://www.delta.exchange/app/futures/trade/{coin}/{coin}USD"
        msg += f'⚪ <a href="{link}">{coin}</a> {sig}\n'
    msg += f"\n<i>Signals: {len(signals)}/{len(results)} | 12H+9H Strategy</i>"
    return msg

async def delete_old_messages(bot):
    while len(sent_messages) > 2:
        old_id = sent_messages.popleft()
        try: await bot.delete_message(chat_id=CHAT_ID, message_id=old_id)
        except: pass

async def background_scan(chat_id, context, is_auto=False):
    results = await do_scan()
    if results:
        txt = format_msg(results)
        sent = await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        sent_messages.append(sent.message_id)
        await delete_old_messages(context.bot)

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("45 coin scan 12H+9H..."); await background_scan(update.effective_chat.id, context, False)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BOT ONLINE - 12H & 9H BREAKUP/DOWN STRATEGY")

async def auto_loop(app):
    await asyncio.sleep(10)
    while True:
        try:
            await background_scan(CHAT_ID, app, True)
            await asyncio.sleep(300)
        except: await asyncio.sleep(30)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd)); app.add_handler(CommandHandler("scan", scan_cmd))
    async def on_startup(a): asyncio.create_task(auto_loop(a))
    app.post_init = on_startup
    app.run_polling(close_loop=False, stop_signals=None)

if __name__ == "__main__": main()
