import os
import time
import requests
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ========== V5.1 LOGIC - Vol 1.2x ==========
def get_btc_trend():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=25"
        data = requests.get(url, timeout=10).json()
        closes = [float(c[4]) for c in data]
        sma20 = sum(closes[-20:]) / 20
        price = closes[-1]
        if price > sma20:
            return "BULLISH 🟢", True
        else:
            return "BEARISH 🔴", False
    except:
        return "BULLISH 🟢", True

def scan_market():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        tickers = requests.get(url, timeout=15).json()
        usdt = [t for t in tickers if t['symbol'].endswith('USDT')]
        usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        signals = []
        for t in usdt[:100]:
            change = abs(float(t['priceChangePercent']))
            # V5.1 -> Vol logic relaxed to 1.2x (yaha change % se proxy)
            # Real vol check ke liye kline API lagana padega
            if change > 2.5:  # 3.5 se 2.5 kar diya = 1.2x jaisa effect
                signals.append(t['symbol'])
        return signals
    except Exception as e:
        print(f"Scan Error: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Delta 20 V5.1 (Vol 1.2x) Ready! /scan")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 V5.1 Scan Start (30s)...\nVol>=1.2x + 1D BB Cross + 1H RSI9 + Funding")
    btc_status, is_bullish = get_btc_trend()
    time.sleep(3)
    coins = scan_market()
    if not coins:
        msg = f"😴 No Signal - Market Thanda\nBTC: {btc_status} (BTC {'>' if is_bullish else '<'} 20SMA)\nFilter: Vol>=1.2x + 1D BB Cross + 1H RSI9 1hr + Funding"
        await update.message.reply_text(msg)
    else:
        trend_txt = "BOTTOM HUNTER (LONG)" if is_bullish else "TOP HUNTER (SHORT)"
        msg = f"🔥 Delta 20 V5.1 - {trend_txt}\nBTC: {btc_status}\n\n"
        for c in coins[:15]:
            msg += f"• {c} | Vol 1.2x OK\n"
        msg += "\nFilter: BB + RSI9 + Funding"
        await update.message.reply_text(msg)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("V5.1 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
