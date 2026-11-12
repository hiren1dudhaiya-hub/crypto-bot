import ccxt, os, pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from ta.volatility import BollingerBands

BOT_TOKEN = os.getenv("BOT_TOKEN")
COINS_49 = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","MATIC/USDT","DOGE/USDT","AVAX/USDT","LINK/USDT","SHIB/USDT","ADA/USDT","DOT/USDT","LTC/USDT","TRX/USDT","ETC/USDT","ATOM/USDT","NEAR/USDT","UNI/USDT","FIL/USDT","APT/USDT","ARB/USDT","OP/USDT","INJ/USDT","SUI/USDT","SEI/USDT","PEPE/USDT","BONK/USDT","WIF/USDT","RNDR/USDT","FET/USDT","AGIX/USDT","GRT/USDT","AAVE/USDT","MKR/USDT","SNX/USDT","CRV/USDT","LDO/USDT","RUNE/USDT","STX/USDT","IMX/USDT","FLOW/USDT","CHZ/USDT","SAND/USDT","MANA/USDT","AXS/USDT","GALA/USDT","ENJ/USDT","CFX/USDT"]

exchange = ccxt.binance({'enableRateLimit': True})

def scan_both():
    tight_list = []
    bb_list = []
    super_list = []

    for symbol in COINS_49:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
            
            # CONDITION 1: 6 Candle Tight <0.9%
            last_6 = df.tail(6)
            last_6['range'] = (last_6['high'] - last_6['low']) / last_6['low'] * 100
            is_tight = (last_6['range'] < 0.9).all()
            avg_range = last_6['range'].mean()

            # CONDITION 2: BB Lower/Upper
            bb = BollingerBands(close=df['close'], window=20, window_dev=2)
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_upper'] = bb.bollinger_hband()
            
            price = df.iloc[-1]['close']
            lower = df.iloc[-1]['bb_lower']
            upper = df.iloc[-1]['bb_upper']
            
            # 0.5% ke andar BB touch
            is_bb_lower = price <= lower * 1.005
            is_bb_upper = price >= upper * 0.995
            is_bb = is_bb_lower or is_bb_upper

            chart = f"https://www.tradingview.com/symbols/{symbol.replace('/','')}/"

            if is_tight and is_bb:
                super_list.append(f"🔥 {symbol} - Tight {avg_range:.2f}% + BB Touch\n{chart}")
            elif is_tight:
                tight_list.append(f"📦 {symbol} - Tight {avg_range:.2f}%\n{chart}")
            elif is_bb:
                side = "LOWER" if is_bb_lower else "UPPER"
                bb_list.append(f"📊 {symbol} - BB {side} Touch\n{chart}")

        except Exception as e:
            continue
    
    return super_list, tight_list, bb_list

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 V7.0 ON - BOTH\n49 Coins | 1H\n1) 6 Candle Tight <0.9%\n2) BB 20 Lower/Upper\nAuto Scan: Har 15 min")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 49 Coins scan (1H)... 30s")
    super_list, tight_list, bb_list = scan_both()

    if not super_list and not tight_list and not bb_list:
        await update.message.reply_text("😴 Abhi koi setup nahi.\n- 6 Tight: 0\n- BB Touch: 0\n15 min me auto check karunga.")
        return

    msg = ""
    if super_list:
        msg += "🚀 *SUPER SIGNAL (Tight + BB):*\n" + "\n\n".join(super_list) + "\n\n"
    if tight_list:
        msg += "📦 *6 CANDLE TIGHT:*\n" + "\n\n".join(tight_list) + "\n\n"
    if bb_list:
        msg += "📊 *BB TOUCH:*\n" + "\n\n".join(bb_list)

    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

async def auto_scan(context: ContextTypes.DEFAULT_TYPE):
    super_list, tight_list, bb_list = scan_both()
    if super_list or tight_list or bb_list:
        # reuse scan logic to send
        await scan_cmd(context.job, context) # simplified auto send via job chat
        # Direct send
        msg = ""
        if super_list: msg += "🚨 AUTO SUPER:\n" + "\n".join(super_list) + "\n\n"
        if tight_list: msg += "AUTO TIGHT:\n" + "\n".join(tight_list)
        if msg:
            await context.bot.send_message(chat_id=context.job.chat_id, text=msg, disable_web_page_preview=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.job_queue.run_repeating(lambda c: asyncio.create_task(auto_scan(c)), interval=900, first=10)
    # Fix for auto_scan chat_id
    async def auto_job(context):
        super_list, tight_list, bb_list = scan_both()
        if super_list:
            txt = "🚨 *AUTO SUPER SIGNAL (Tight+BB)*\n\n" + "\n\n".join(super_list)
            await context.bot.send_message(chat_id=context.job.chat_id, text=txt, parse_mode="Markdown", disable_web_page_preview=True)
        elif tight_list or bb_list:
            txt = ""
            if tight_list: txt += "📦 *AUTO 6 TIGHT*\n" + "\n\n".join(tight_list) + "\n\n"
            if bb_list: txt += "📊 *AUTO BB*\n" + "\n\n".join(bb_list)
            await context.bot.send_message(chat_id=context.job.chat_id, text=txt, parse_mode="Markdown", disable_web_page_preview=True)

    app.job_queue.run_repeating(auto_job, interval=900, first=15)
    app.run_polling()

if __name__ == "__main__":
    main()
