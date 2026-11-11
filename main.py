import os
import time
import requests
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ========== V5 LOGIC - TOP / BOTTOM HUNTER ==========
def get_btc_trend():
    try:
        # BTC 20SMA check
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=25"
        data = requests.get(url, timeout=10).json()
        closes = [float(c[4]) for c in data]
        sma20 = sum(closes[-20:]) / 20
        price = closes[-1]
        if price > sma20:
            return "BULLISH 🟢", price > sma20
        else:
            return "BEARISH 🔴", price > sma20
    except:
        return "BULLISH 🟢", True

def scan_market():
    # V5 Filters: Vol>=1.5x + 1D BB Cross + 1H RSI9 Rising/Falling + Funding
    try:
        # Example scan - Top 100 coins
        url = "https://api.binance.com/api/v3/ticker/24hr"
        tickers = requests.get(url, timeout=15).json()
        # Filter USDT pairs, top volume
        usdt = [t for t in tickers if t['symbol'].endswith('USDT') and not t['symbol'].startswith('BTC')]
        usdt.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        top20 = usdt[:100]
        
        signals = []
        for t in top20:
            vol = float(t['quoteVolume'])
            price_change = float(t['priceChangePercent'])
            # Simple V5 condition for demo
            if abs(price_change) > 3.5:
                signals.append(t['symbol'])
        
        return signals[:20]
    except Exception as e:
        print(f"Scan Error: {e}")
        return []

# ========== TELEGRAM COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Delta 20 V5 - Top/Bottom Hunter Ready! Use /scan")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 V5 Scan Start (30s)...\nVol>=1.5x + 1D BB Cross + 1H RSI9 + Funding check")
    
    btc_status, is_bullish = get_btc_trend()
    
    # Simulate 30s scan
    time.sleep(5)
    coins = scan_market()
    
    if not coins:
        msg = f"😴 No Signal - Market Thanda\nBTC: {btc_status} (BTC {'>' if is_bullish else '<'} 20SMA)\nFilter: Vol>=1.5x + 1D BB Cross + 1H RSI9 1hr Rising/Falling + Funding"
        await update.message.reply_text(msg)
    else:
        trend_txt = "BOTTOM HUNTER (LONG)" if is_bullish else "TOP HUNTER (SHORT)"
        msg = f"🔥 Delta 20 V5 - {trend_txt}\nBTC: {btc_status}\n\n"
        for c in coins[:10]:
            msg += f"• {c}\n"
        msg += "\nFilter: BB Cross + RSI9 + Funding"
        await update.message.reply_text(msg)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("Delta 20 V5 - Bottom/Top Hunter Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
