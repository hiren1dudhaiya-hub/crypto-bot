import os, time, requests, threading
from flask import Flask
import pandas as pd

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHATID")

COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","LINKUSDT","LTCUSDT","BCHUSDT","UNIUSDT","XLMUSDT","ETCUSDT","FILUSDT","APTUSDT","ARBUSDT","OPUSDT","NEARUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "Delta 20 V5 - Bottom + Top Hunter"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(f"TG Error: {e}")

def get_klines(symbol, interval="1d", limit=100):
    for _ in range(3):
        try:
            url = "https://data-api.binance.vision/api/v3/klines"
            r = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10).json()
            if not isinstance(r, list): continue
            df = pd.DataFrame(r, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
            df['close'] = df['close'].astype(float); df['qav'] = df['qav'].astype(float)
            return df
        except: time.sleep(1)
    return None

def get_funding_rate(symbol):
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}", timeout=5).json()
        return float(r.get('lastFundingRate', 0)) * 100
    except: return 0

def calculate_rsi(series, period=9):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    return 100 - (100 / (1 + gain/loss))

def scan_market(manual=False):
    btc_d = get_klines("BTCUSDT", "1d", 60)
    if btc_d is None: return
    btc_d['sma20'] = btc_d['close'].rolling(20).mean()
    btc_bullish = btc_d['close'].iloc[-1] > btc_d['sma20'].iloc[-1]
    btc_status = 'BULLISH 🟢' if btc_bullish else 'BEARISH 🔴'
    
    signals = []
    
    for symbol in COINS:
        time.sleep(0.3)
        d = get_klines(symbol, "1d", 100); h = get_klines(symbol, "1h", 100)
        if d is None or h is None or len(d) < 30: continue
        
        d['sma20'] = d['close'].rolling(20).mean(); d['vol_avg'] = d['qav'].rolling(20).mean()
        vol_ratio = d['qav'].iloc[-1] / d['vol_avg'].iloc[-1] if d['vol_avg'].iloc[-1]>0 else 0
        h['rsi9'] = calculate_rsi(h['close'], 9)
        
        cross_up = d['close'].iloc[-2] < d['sma20'].iloc[-2] and d['close'].iloc[-1] > d['sma20'].iloc[-1]
        cross_down = d['close'].iloc[-2] > d['sma20'].iloc[-2] and d['close'].iloc[-1] < d['sma20'].iloc[-1]
        rsi_rising = h['rsi9'].iloc[-1] > h['rsi9'].iloc[-2]
        rsi_falling = h['rsi9'].iloc[-1] < h['rsi9'].iloc[-2]
        price = d['close'].iloc[-1]; funding = get_funding_rate(symbol)

        # 1. NORMAL BUY (Bull Market Breakout)
        if btc_bullish and vol_ratio >= 1.5 and cross_up and rsi_rising and funding < 0.10:
            signals.append(f"🚀 BUY {symbol} | {price:.2f} | Vol {vol_ratio:.1f}x")

        # 2. NORMAL SELL (Bear Market Breakdown)
        if not btc_bullish and vol_ratio >= 1.5 and cross_down and rsi_falling and funding > -0.10:
            signals.append(f"🔻 SELL {symbol} | {price:.2f} | Vol {vol_ratio:.1f}x")

        # 3. BOTTOM HUNTER - PRO KA BAAP (Bear me Long)
        if not btc_bullish and funding < -0.002 and vol_ratio >= 1.0 and rsi_rising:
            signals.append(f"💎 BOTTOM LONG {symbol} | {price:.2f} | Fund {funding:.4f}% (Shorts Trap) | RSI {h['rsi9'].iloc[-1]:.0f}↑")

        # 4. TOP HUNTER - NAYA (Bull me Short) - Sabse zyada paisa yahi deta hai
        if btc_bullish and funding > 0.08 and vol_ratio >= 1.0 and rsi_falling:
            signals.append(f"💀 TOP SHORT {symbol} | {price:.2f} | Fund {funding:.4f}% (Longs Trap) | RSI {h['rsi9'].iloc[-1]:.0f}↓")

    if signals:
        msg = f"🔥 **Delta 20 V5** 🔥\nBTC: {btc_status}\n\n" + "\n".join(signals)
        send_telegram(msg)
    elif manual:
        send_telegram(f"😴 **No Signal**\nBTC: {btc_status}\nChecked: Breakout + Bottom + Top")

def run_scan_background(manual):
    threading.Thread(target=scan_market, args=(manual,), daemon=True).start()

def telegram_polling():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            r = requests.get(url, timeout=25).json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                if "/scan" in update.get("message", {}).get("text", ""):
                    send_telegram("🔍 V5 Scan Start (30s)...")
                    run_scan_background(True)
            time.sleep(2)
        except Exception as e: print(f"Polling: {e}"); time.sleep(5)

def auto_scan_loop():
    time.sleep(20)
    while True:
        print("Auto Scan V5..."); scan_market(False); time.sleep(1800)

threading.Thread(target=telegram_polling, daemon=True).start()
threading.Thread(target=auto_scan_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
