import os, time, requests, threading
from flask import Flask
import pandas as pd

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","LINKUSDT","LTCUSDT","BCHUSDT","UNIUSDT","XLMUSDT","ETCUSDT","FILUSDT","APTUSDT","ARBUSDT","OPUSDT","NEARUSDT"]

app = Flask(__name__)
@app.route('/')
def home(): return "Delta 20 V3 FINAL - Vol 1.5x + BB + RSI9 + Funding + SMA20"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e: print(f"TG Error: {e}")

def get_klines(symbol, interval="1d", limit=100):
    for _ in range(3):
        try:
            url = "https://data-api.binance.vision/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if not isinstance(data, list): continue
            df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
            df['close'] = df['close'].astype(float)
            df['qav'] = df['qav'].astype(float)
            return df
        except: time.sleep(1)
    return None

def get_funding_rate(symbol):
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        r = requests.get(url, params=params, timeout=5).json()
        return float(r.get('lastFundingRate', 0)) * 100
    except:
        return 0

def calculate_rsi(series, period=9):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_market(manual=False):
    btc_d = get_klines("BTCUSDT", "1d", 60)
    if btc_d is None: return None
    btc_d['sma20'] = btc_d['close'].rolling(20).mean()
    btc_bullish = btc_d['close'].iloc[-1] > btc_d['sma20'].iloc[-1]
    btc_status = 'BULLISH 🟢 (BTC > 20SMA)' if btc_bullish else 'BEARISH 🔴 (BTC < 20SMA)'
    
    buy_signals = []
    sell_signals = []
    
    for symbol in COINS:
        time.sleep(0.3)
        d = get_klines(symbol, "1d", 100)
        h = get_klines(symbol, "1h", 100)
        if d is None or h is None or len(d) < 30 or len(h) < 15: continue
        
        d['sma20'] = d['close'].rolling(20).mean()
        d['vol_avg'] = d['qav'].rolling(20).mean()
        vol_ratio = d['qav'].iloc[-1] / d['vol_avg'].iloc[-1] if d['vol_avg'].iloc[-1] > 0 else 0
        
        h['rsi9'] = calculate_rsi(h['close'], 9)
        
        cross_up = d['close'].iloc[-2] < d['sma20'].iloc[-2] and d['close'].iloc[-1] > d['sma20'].iloc[-1]
        cross_down = d['close'].iloc[-2] > d['sma20'].iloc[-2] and d['close'].iloc[-1] < d['sma20'].iloc[-1]
        
        # 1 Ghante wala - Current Hour vs Previous Hour
        rsi_rising = h['rsi9'].iloc[-1] > h['rsi9'].iloc[-2]
        rsi_falling = h['rsi9'].iloc[-1] < h['rsi9'].iloc[-2]
        
        price = d['close'].iloc[-1]
        funding = get_funding_rate(symbol)
        
        funding_ok_for_buy = funding < 0.10
        funding_ok_for_sell = funding > -0.10

        buy_cond = btc_bullish and vol_ratio >= 1.5 and cross_up and rsi_rising and funding_ok_for_buy
        sell_cond = (not btc_bullish) and vol_ratio >= 1.5 and cross_down and rsi_falling and funding_ok_for_sell
        
        if buy_cond:
            buy_signals.append(f"🚀 **BUY {symbol}** | {price:.3f} | BB↑ | 1H RSI9 {h['rsi9'].iloc[-2]:.1f}->{h['rsi9'].iloc[-1]:.1f}↑ | Vol {vol_ratio:.2f}x | Fund {funding:.4f}%")
        if sell_cond:
            sell_signals.append(f"🔻 **SELL {symbol}** | {price:.3f} | BB↓ | 1H RSI9 {h['rsi9'].iloc[-2]:.1f}->{h['rsi9'].iloc[-1]:.1f}↓ | Vol {vol_ratio:.2f}x | Fund {funding:.4f}%")

    all_signals = buy_signals + sell_signals
    if all_signals:
        msg = f"🔥 **Delta 20 V3 FINAL** 🔥\nBTC: {btc_status} | Vol>=1.5x\n\n" + "\n".join(all_signals)
        send_telegram(msg); return msg
    else:
        if manual:
            msg = f"😴 **No Signal - Market Thanda**\nBTC: {btc_status}\nFilter: Vol>=1.5x + 1D BB Cross + 1H RSI9 1hr Rising/Falling + Funding"
            send_telegram(msg); return msg
        return None

def telegram_polling():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            r = requests.get(url, timeout=25).json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                text = update.get("message", {}).get("text", "")
                if "/scan" in text:
                    send_telegram("🔍 V3 FINAL Scan Start...")
                    scan_market(manual=True)
            time.sleep(2)
        except Exception as e: print(f"Polling: {e}"); time.sleep(5)

def auto_scan_loop():
    time.sleep(20)
    while True:
        print("Auto Scan V3..."); scan_market(manual=False); time.sleep(1800)

threading.Thread(target=telegram_polling, daemon=True).start()
threading.Thread(target=auto_scan_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
