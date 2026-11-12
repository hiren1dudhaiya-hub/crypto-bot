import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- ENV FIX ---
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN")
CHAT_ID_ENV = os.getenv("CHAT_ID")
CHAT_ID = int(CHAT_ID_ENV) if CHAT_ID_ENV and CHAT_ID_ENV.isdigit() else None

BINANCE_API = "https://data-api.binance.vision"
TOP_N = 100

async def get_top_symbols(session):
    url = f"{BINANCE_API}/api/v3/ticker/24hr"
    async with session.get(url) as r:
        data = await r.json()
        # USDT pairs only, sorted by volume
        usdt = [d for d in data if d['symbol'].endswith('USDT')]
        usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [d['symbol'] for d in usdt[:TOP_N]]

async def get_klines(session, symbol):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=15m&limit=6"
    try:
        async with session.get(url, timeout=10) as r:
            klines = await r.json()
            if not isinstance(klines, list) or len(klines) < 6:
                return None
            ranges = []
            for k in klines:
                high = float(k[2]); low = float(k[3])
                if low == 0: return None
                rng = ((high - low) / low) * 100
                ranges.append(rng)
            avg_range = sum(ranges) / len(ranges)
            return avg_range, ranges
    except:
        return None

async def do_scan():
    results = []
    async with aiohttp.ClientSession() as session:
        symbols = await get_top_symbols(session)
        for sym in symbols:
            data = await get_klines(session, sym)
            if not data: continue
            avg_range, all_ranges = data
            # V16 LOGIC: Avg < 0.9 = TIGHT
            if avg_range < 0.9:
                status = "✅"
            else:
                status = "❌"
            results.append((sym, avg_range, status))
    
    # Sort by tightest first
    results.sort(key=lambda x: x[1])
    return results

def format_msg(results):
    msg = f"🔍 DELTA 20 SCANNER - V16 FAIL-SAFE\nBINANCE ONLY - data-api.binance.vision se\nHar 15 min\n\n"
    msg += f"Top {len(results)} scanned:\n"
    for sym, avg, status in results[:30]: # top 30 tightest show
        coin = sym.replace('USDT','')
        msg += f"{coin} {avg:.2f}% {status}\n"
    
    tight_count = sum(1 for r in results if r[2] == "✅")
    msg += f"\nTotal Tight: {tight_count}/{len(results)}"
    return msg

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning... V16 chal raha hai...")
    results = await do_scan()
    msg = format_msg(results)
    await update.message.reply_text(msg)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Chat ID batayega taki env me dal sake
    cid = update.effective_chat.id
    await update.message.reply_text(f"Bot Active ✅ V16\nYour Chat ID: {cid}\nIsko FadeHost me CHAT_ID me dal do.")

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID:
        print("CHAT_ID not set, skipping auto msg")
        return
    results = await do_scan()
    msg = format_msg(results)
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN / TELEGRAM_BOT_TOKEN missing!")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("scan", scan_command))
    
    # Auto every 15 min
    if CHAT_ID:
        app.job_queue.run_repeating(auto_job, interval=900, first=10)
        print(f"Auto msg enabled for CHAT_ID {CHAT_ID} every 15m")
    else:
        print("CHAT_ID not found, auto disabled. /start se ID leke env me dalo")

    print("Bot started V16")
    app.run_polling()

if __name__ == "__main__":
    main()
