async def get_data(session, symbol, sem):
    try:
        # --- SIRF 30m SE 90m BANAO ---
        url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval=30m&limit=150"
        async with sem:
            async with session.get(url, timeout=10) as r:
                kl30 = await r.json()

        if not isinstance(kl30, list) or len(kl30) < 60: return None

        # 90m CANDLE BUILD (3 x 30m = 1 x 90m)
        closes90, highs90, lows90 = [], [], []
        for i in range(0, len(kl30)-2, 3):
            c1, c2, c3 = kl30[i], kl30[i+1], kl30[i+2]
            closes90.append(float(c3[4]))
            highs90.append(max(float(c1[2]), float(c2[2]), float(c3[2])))
            lows90.append(min(float(c1[3]), float(c2[3]), float(c3[3])))

        closes90 = np.array(closes90)
        highs90 = np.array(highs90)
        lows90 = np.array(lows90)

        if len(closes90) < 20: return None

        # --- INDICATORS ON 90m ---
        rsi9 = calc_rsi(closes90, 9)[-1]
        ma3 = sma(closes90, 3)
        rsi14 = calc_rsi(closes90, 14)[-1]
        ma9 = sma(closes90, 9)

        # --- SIRF 90m BREAKUP / BREAKDOWN ---
        high_break = highs90[-1] > highs90[-2]  # 90m HIGH BREAKUP
        low_break = lows90[-1] < lows90[-2]     # 90m LOW BREAKDOWN

        coin = symbol.replace("USDT","")
        rsi_str = f"R9:{rsi9:.0f} M3:{ma3:.0f} | R14:{rsi14:.0f} M9:{ma9:.0f}"

        # LONG = 90m HIGH BREAKUP + BULL
        if high_break and (rsi9 > ma3) and (rsi14 > ma9):
            return (coin, f"LONG | {rsi_str} | 90m HIGH BREAK ↑", symbol, True)
        
        # SHORT = 90m LOW BREAKDOWN + BEAR
        if low_break and (rsi9 < ma3) and (rsi14 < ma9):
            return (coin, f"SHORT | {rsi_str} | 90m LOW BREAK ↓", symbol, True)

        # WAIT
        status = "BULL" if rsi9 > ma3 else "BEAR" if rsi9 < ma3 else "MIX"
        sig = f"{status} Tight | {rsi_str}"
        return (coin, sig, symbol, False)

    except:
        return None
