import os
import ccxt
import pandas as pd
import ta
import time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

TOP_49 = [
"BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","DOGE/USDT","ADA/USDT","AVAX/USDT","LINK/USDT","LTC/USDT","DOT/USDT","TRX/USDT","SHIB/USDT","PEPE/USDT","ARB/USDT","OP/USDT","SUI/USDT","WIF/USDT","BONK/USDT",
"UNI/USDT","ATOM/USDT","ETC/USDT","FIL/USDT","APT/USDT","NEAR/USDT","TAO/USDT","RNDR/USDT","FET/USDT","INJ/USDT","SEI/USDT","JUP/USDT","PYTH/USDT","STX/USDT","IMX/USDT","LDO/USDT","MKR/USDT","AAVE/USDT","CRV/USDT","SAND/USDT","MANA/USDT","ENA/USDT","ONDO/USDT","WLD/USDT","AR/USDT","HBAR/USDT","VET/USDT","CHZ/USDT","ENS/USDT","ALGO/USDT"
]

exchange = ccxt.binance()
LAST_CHAT_ID = {"id": None}

def check_signal(sym):
    try:
        ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2)
        lower = bb.bollinger_lband().iloc[-1]
        upper = bb.bollinger_hband().iloc[-1]
        price = df['c'].iloc[-1]
        rsi_indicator = ta.momentum.RSIIndicator(df['c'], window=9).rsi()
        rsi = rsi_indicator.iloc[-1]
        rsi_sma = ta.trend.SMAIndicator(rsi_indicator, window=9).sma_indicator().iloc[-1]
        change = ((df['c'].iloc[-1] - df['c'].iloc[-24]) / df['c'].iloc[-24]) * 100
        if price <= lower and rsi < 35 and rsi > rsi_sma and change > 1.0:
            return f"✅ LONG {sym}\nPrice: {price:.4f}\nRSI9: {rsi:.1f} | 24h: {change:.2f}%\nSetup: 75% Winrate"
        if price >= upper and rsi > 65 and rsi < rsi_sma and change < -1.0:
            return f"🔻 SHORT {sym}\nPrice: {price:.4f}\nRSI9: {rsi:.1f} | 24h: {change:.2f}%"
    except: return None
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    LAST_CHAT_ID["id"] = update.effective_chat.id
    await update.message.reply_text("🤖 V6.2 ON - 49 Coins\nAuto Scan: Har 15 min\nSignal milega to khud bhejunga\n/scan se abhi check kar sakte ho")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    LAST_CHAT_ID["id"] = update.effective_chat.id
    await update.message.reply_text("🔍 49 Coins scan (1H)... 30s")
    found = []
    for sym in TOP_49:
        sig = check_signal(sym)
        if sig: found.append(sig)
        time.sleep(0.3)
    if not found:
        await update.message.reply_text("😴 49 me se abhi koi Lower/Upper BB pe nahi. 15 min me auto check karunga.")
    else:
        await update.message.reply_text("🔥 SIGNAL:\n\n" + "\n\n".join(found))

async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = LAST_CHAT_ID["id"]
    if not chat_id: return
    found = []
    for sym in TOP_49:
        sig = check_signal(sym)
        if sig: found.append(sig)
        await asyncio.sleep(0.5)
    if found:
        msg = "⏰ AUTO 15Min SIGNAL (49):\n\n" + "\n\n".join(found) + "\n\nDelta pe check karo."
        await context.bot.send_message(chat_id=chat_id, text=msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    # Har 15 min = 900 sec
    app.job_queue.run_repeating(auto_job, interval=900, first=30)
    print("V6.2 Auto 15min started")
    app.run_polling()

if __name__ == "__main__":
    main()
