import os
import asyncio
import aiohttp
from collections import deque
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8465758405:AAH_YOUR_TOKEN_HERE"
CHAT_ID = int(os.getenv("CHAT_ID") or "7086505670")
BINANCE_API = "https://data-api.binance.vision"

sent_messages = deque(maxlen=100)

DELTA_COINS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT",
    "ADAUSDT","AVAXUSDT","LINKUSDT","BCHUSDT","LTCUSDT","XLMUSDT",
    "DOTUSDT","ATOMUSDT","ETCUSDT","FILUSDT","TRXUSDT","SHIBUSDT",
    "UNIUSDT","PEPEUSDT","ARBUSDT","OPUSDT","NEARUSDT","APTUSDT",
    "SUIUSDT","TAOUSDT","RENDERUSDT","AAVEUSDT","MKRUSDT","INJUSDT",
    "LDOUSDT","GRTUSDT","STXUSDT","IMXUSDT","HBARUSDT","VETUSDT",
    "QNTUSDT","ALGOUSDT","EGLDUSDT","FTMUSDT"
]

async def get_data(session, symbol, sem):
    url_1h = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1h&limit=6"
    url_1m = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=1m&limit=420"
    async with sem:
        try:
            async with session.get(url_1h, timeout=10) as r:
                kl = await r.json()
                if not isinstance(kl, list) or len(kl) < 6: return None
                highs = [float(k[2]) for k in kl]
                lows = [float(k[3]) for k in kl]
                closes = [float(k[4]) for k in kl]
                avg_range = sum([((h-l)/l)*100 for h,l in zip(highs,lows)]) / 6
                curr = closes[-1]
                high6 = max(highs); low6 = min(lows)
                coin = symbol.replace("USDT","")
                st = "✅" if avg_range < 0.9 else "❌"
                # Base direction without volume
                if (high6-curr)/curr*100 < 0.15: base_dir = "🚀 BUY"
                elif (curr-low6)/curr*100 < 0.15: base_dir = "🔻 SELL"
                else: base_dir = "Tight"

            # 1-min Volume Spike - EXACT 6.67X filter
            spike_X = 0.0
            try:
                async with session.get(url_1m, timeout=10) as r2:
                    kl_1m = await r2.json()
                    if isinstance(kl_1m, list) and len(kl_1m) > 360:
                        vols = [float(k[5]) for k in kl_1m]
                        avg_vol = sum(vols[-361:-1]) / 360  # 6h avg (1m candles)
                        curr_vol = vols[-1]  # current 1m candle
                        if avg_vol > 0: spike_X = curr_vol / avg_vol
            except: pass

            # FINAL SIGNAL LOGIC - SIRF 6.67X
            if st == "✅" and spike_X >= 6.67:
                direction = f"{base_dir} | Vol {spike_X:.1f}X 🔥"
            else:
                # Tight hai par volume kam hai to signal nahi
                if st == "✅":
                    direction = f"Tight | Vol {spike_X:.1f}X"
                else:
                    direction = base_dir
            
            return (coin, avg_range, st, direction, symbol, spike_X)
        except: return None

async def do_scan():
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(15)
        results = await asyncio.gather(*[get_data(session, s, sem) for s in DELTA_COINS])
        final = [r for r in results if r]
        final.sort(key=lambda x: x[1])
        return final

def format_msg(results):
    tight = len([r for r in results if r[2] == "✅" and "Vol" in r[3] and float(r[3].split("Vol")[1].split("X")[0].strip()) >= 6.67])
    # Simple tight count
    tight_total = len([r for r in results if r[2] == "✅"])
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    time_str = ist.strftime("%d-%b %I:%M %p IST")
    msg = f"🔍 <b>DELTA 20 - (1H x 6) + 1m Vol 6.67X | {len(results)} Coins</b>\n"
    msg += f"<i>⏰ {time_str} | Auto 5 min</i>\n\n"
    for coin, avg, st, direction, symbol, spike_X in results:
        link = f"https://www.delta.exchange/app/futures/trade/{coin}/{coin}USD?chart_orderbook_tab=chart"
        msg += f'<a href="{link}">{coin}</a> {avg:.2f}% {st} {direction}\n'
    msg += f"\n<b>Signal(Vol>=6.67X): {tight}/{tight_total} Tight</b>"
    return msg

async def delete_old_messages(bot):
    while len(sent_messages) > 2:
        old_id = sent_messages.popleft()
        try:
            await bot.delete_message(chat_id=CHAT_ID, message_id=old_id)
            await asyncio.sleep(0.3)
        except: pass

async def background_scan(chat_id, context, is_auto=False):
    try:
        results = await do_scan()
        if results:
            txt = format_msg(results)
            if is_auto: txt = f"🤖 <b>AUTO SIGNAL - 5 MIN | Vol 6.67X</b>\n\n" + txt
            sent = await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            sent_messages.append(sent.message_id)
            if is_auto: await delete_old_messages(context.bot)
    except Exception as e: print(f"Error: {e}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning 6.67X Vol filter...")
    await background_scan(update.effective_chat.id, context, False)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ BOT ONLINE\nFilter: Range<0.9% + Vol>=6.67X (1m)\nAuto: 5 min, Last 2 msgs\nID: {update.effective_chat.id}")

async def auto_loop(app):
    await asyncio.sleep(10)
    try: await background_scan(CHAT_ID, app, True)
    except: pass
    while True:
        try:
            await asyncio.sleep(300)
            await background_scan(CHAT_ID, app, True)
        except Exception as e:
            print(f"Loop error {e}")
            await asyncio.sleep(30)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    async def on_startup(a): asyncio.create_task(auto_loop(a))
    app.post_init = on_startup
    print("Bot starting - 5min + 6.67X Vol + Auto-delete...")
    app.run_polling(close_loop=False, stop_signals=None)

if __name__ == "__main__":
    main()
