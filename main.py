import ccxt, pandas as pd, ta, time, os
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

# Tere purane 19 + naye 30 = 49 coins (MATIC/POL hataya)
TOP_49 = [
# Purane 19
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","LTCUSDT","DOTUSDT","TRXUSDT","SHIBUSDT","PEPEUSDT","ARBUSDT","OPUSDT","SUIUSDT","WIFUSDT","BONKUSDT",
# Naye 30 - Delta + Binance common
"UNIUSDT","ATOMUSDT","ETCUSDT","FILUSDT","APTUSDT","NEARUSDT","TAOUSDT","RNDRUSDT","FETUSDT","INJUSDT","SEIUSDT","JUPUSDT","PYTHUSDT","STXUSDT","IMXUSDT","LDOUSDT","MKRUSDT","AAVEUSDT","CRVUSDT","SANDUSDT","MANAUSDT","ENAUSDT","ONDOUSDT","WLDUSDT","ARUSDT","HBARUSDT","VETUSDT","CHZUSDT","ENSUSDT","ALGOUSDT"
]

exchange = ccxt.binance()

def check_signal(sym):
    try:
        ohlcv = exchange.fetch_ohlcv(sym, '1h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        
        # BB 20 2
        bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2)
        lower = bb.bollinger_lband().iloc[-1]
        price = df['c'].iloc[-1]
        
        # RSI 9 + SMA 9
        rsi = ta.momentum.RSIIndicator(df['c'], window=9).rsi().iloc[-1]
        rsi_sma = ta.trend.SMAIndicator(ta.momentum.RSIIndicator(df['c'], window=9).rsi(), window=9).sma_indicator().iloc[-1]
        
        # 24h Change > 2%
        change = ((df['c'].iloc[-1] - df['c'].iloc[-24]) / df['c'].iloc[-24]) * 100
        
        if price <= lower and rsi < 35 and rsi > rsi_sma and change > 2.0:
            return f"✅ LONG {sym} | Price: {price} | RSI 9: {rsi:.2f} | 24h: {change:.2f}%"
    except Exception as e:
        print(f"{sym} error {e}")
    return None

def scan():
    print(f"Scanning 49 coins 1H BB 20 2...")
    found = []
    for sym in TOP_49:
        sig = check_signal(sym)
        if sig:
            found.append(sig)
        time.sleep(0.3)
    
    if not found:
        msg = "V6.1 Scan: 49 coins checked, abhi koi Lower BB pe nahi hai. Market bullish hai."
    else:
        msg = "🔥 V6.1 SIGNAL (49 Coins):\n\n" + "\n".join(found)
    
    # Telegram pe bhej (Tera chat id daal)
    # bot.send_message(chat_id=YOUR_CHAT_ID, text=msg)
    print(msg)

if __name__ == "__main__":
    scan()
