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
    url = "{}/api/v3/klines?symbol={}&interval=30m&limit=100".format(BINANCE_API, symbol)
    async with sem:
        try:
            async with session.get(url, timeout=10) as r:
                kl = await r.json()
                if not isinstance(kl, list) or len(kl) < 50: return None
                closes = np.array([float(k[4]) for k in kl]); highs = np.array([float(k[2]) for k in kl]); lows = np.array([float(k[3]) for k in kl]); vols = np.array([float(k[5]) for k in kl])
                sma20 = np.mean(closes[-20:]); std20 = np.std(closes[-20:]); bb_up = sma20 + std20*2; bb_low = sma20 - std20*2
                tr = np.maximum(highs-lows, np.maximum(np.abs(highs-np.roll(closes,1)), np.abs(lows-np.roll(closes,1))))[1:]
                atr20 = np.mean(tr[-20:]); kc_up = sma20 + atr20*1.5; kc_low = sma20 - atr20*1.5
                max_sq=0; sc=0
                for i in range(-25, -1):
                    if i-19 < -len(closes): continue
                    s = np.mean(closes[i-19:i+1]); sd = np.std(closes[i-19:i+1]); bbu = s + sd*2; bbl = s - sd*2; tr_i = tr[i] if abs(i) <= len(tr) else atr20; kcu = s + tr_i*1.5; kcl = s - tr_i*1.5
                    if bbu < kcu and bbl > kcl: sc+=1; max_sq=max(max_sq, sc)
                    else: sc=0
                is_sq_now = (bb_up < kc_up) and (bb_low > kc_low); fire = max_sq >= 8 and not is_sq_now
                rsi_series = calc_rsi(closes, 9); rsi9 = float(rsi_series[-1]); rsi_ma9 = float(np.mean(rsi_series[-9:])); rsi_prev = float(rsi_series[-2]); ma_prev = float(np.mean(rsi_series[-10:-1]))
                cross_up = rsi_prev < ma_prev and rsi9 > rsi_ma9; cross_down = rsi_prev > ma_prev and rsi9 < rsi_ma9
                avg_vol20 = np.mean(vols[-21:-1]); vol_mult = vols[-1]/avg_vol20 if avg_vol20>0 else 0
                coin = symbol.replace("USDT",""); vol_str = " Vol{:.1f}x".format(vol_mult)
                # VOLUME CONDITION HATAYA - SIRF FIRE + CROSS SE SIGNAL
                if fire:
                    if cross_up and rsi9 > 50: return (coin, "LONG | RSI {:.0f} SQ{} Fire{} FIRE".format(rsi9, max_sq, vol_str), symbol, True)
                    if cross_down and rsi9 < 50: return (coin, "SHORT | RSI {:.0f} SQ{} Fire{} FIRE".format(rsi9, max_sq, vol_str), symbol, True)
                sig = "Tight | RSI {:.0f} SQ{}".format(rsi9, max_sq) + (" Fire" if fire else "") + vol_str
                return (coin, sig, symbol, False)
        except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(10)
        results = await asyncio.gather(*[get_data(session,s,sem) for s in DELTA_COINS])
        final = [r for r in results if r is not None]; final.sort(key=lambda x: (0 if x[3] else 1, x[0])); return final

def format_msg(results):
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    time_str = ist.strftime("%I:%M %p IST - %d %b")
    signals = []; fire_watch = []; tight_list = []
    for coin,sig,symbol,is_sig in results:
        if is_sig: signals.append((coin,sig,symbol))
        elif "Fire" in sig: fire_watch.append((coin,sig,symbol))
        else: tight_list.append((coin,sig,symbol))
    msg = "<b>AUTO 5 MIN - {} COINS | {}</b>\n".format(len(results), time_str)
    msg += "<b>DELTA 45 - RSI MA CROSS | 30m</b>\n\n"
    for coin,sig,symbol in signals:
        link = "https://www.delta.exchange/app/futures/trade/{}/{}USD".format(coin, coin)
        if "LONG" in sig:
            sig2 = sig.replace("LONG", "<b>LONG</b>").replace("FIRE", "<b>FIRE</b>")
            msg += '🟩 <a href="{}">{}</a> {}\n'.format(link, coin, sig2)
        else:
            sig2 = sig.replace("SHORT", "<b>SHORT</b>").replace("FIRE", "<b>FIRE</b>")
            msg += '🟥 <a href="{}">{}</a> {}\n'.format(link, coin, sig2)
    for coin,sig,symbol in fire_watch:
        link = "https://www.delta.exchange/app/futures/trade/{}/{}USD".format(coin, coin)
        sig2 = sig.replace("Fire", "<b>Fire</b>")
        msg += '🟧 <a href="{}">{}</a> {}\n'.format(link, coin, sig2)
    for coin,sig,symbol in tight_list:
        link = "https://www.delta.exchange/app/futures/trade/{}/{}USD".format(coin, coin)
        msg += '⚪ <a href="{}">{}</a> {}\n'.format(link, coin, sig)
    msg += "\n<i>Signals: {}/{} | Fire: {}/{} | Vol Info</i>".format(len(signals), len(results), len(fire_watch), len(results))
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
    await update.message.reply_text("45 coin scan..."); await background_scan(update.effective_chat.id, context, False)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BOT ONLINE - Vol Filter Removed")

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
