import ccxt
import time
import os
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TOP_10 = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","MATIC/USDT","DOGE/USDT","AVAX/USDT","LINK/USDT","SHIB/USDT"]

def send_tg(msg):
    if not BOT_TOKEN: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

# Binance exchange (public, no key needed for klines)
exchange = ccxt.binance({
    'enableRateLimit': True,
})

def check_6_candle():
    print(f"Scanning: {datetime.now()}")
    for symbol in TOP_10:
        try:
            # 1h ke 10 candle lo
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=10)
            # ohlcv = [timestamp, open, high, low, close, volume]
            last_6 = ohlcv[-6:]
            
            tight_count = 0
            for c in last_6:
                high, low = c[2], c[3]
                pct = (high - low) / low * 100
                if pct < 0.9:
                    tight_count += 1
            
            if tight_count == 6:
                avg_range = sum((c[2]-c[3])/c[3]*100 for c in last_6)/6
                price = last_6[-1][4]
                msg = f"🚀 *6 CANDLE TIGHT*\n\nCoin: {symbol}\nPrice: {price}\nAvg 6H Range: {avg_range:.3f}%\nBreakout Ready!"
                send_tg(msg)
                print(f"ALERT: {symbol} - {avg_range:.3f}%")
                time.sleep(1) # rate limit

        except Exception as e:
            print(f"Error {symbol}: {e}")
            time.sleep(2)

if __name__ == "__main__":
    send_tg("✅ Crypto Bot Started - Binance 6 Candle Scan")
    while True:
        check_6_candle()
        time.sleep(900) # 15 min = 900 sec
