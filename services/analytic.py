import ccxt
import pandas as pd
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands

# Binance exchange public data
exchange = ccxt.binance()

def get_technical_analysis(asset="BTC"):
    symbol = f"{asset.upper()}/USDT"
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=500)

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # RSI
    rsi_indicator = RSIIndicator(close=df['close'], window=24)
    df['RSI'] = rsi_indicator.rsi()

    # MACD
    macd_indicator = MACD(close=df['close'])
    df['MACD'] = macd_indicator.macd()
    df['MACD_signal'] = macd_indicator.macd_signal()
    df['MACD_histogram'] = macd_indicator.macd_diff()

    # Bollinger Bands
    bb_indicator = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_upper'] = bb_indicator.bollinger_hband()
    df['BB_middle'] = bb_indicator.bollinger_mavg()
    df['BB_lower'] = bb_indicator.bollinger_lband()

    # Moving Averages
    df['MA20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['MA50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['MA200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()

    latest = df.iloc[-1]

    # RSI analysis
    if latest['RSI'] > 70:
        rsi_signal = "Overbought ⚠️"
    elif latest['RSI'] < 30:
        rsi_signal = "Oversold 🔄"
    else:
        rsi_signal = "Neutral ↔️"

    # MACD analysis
    if latest['MACD'] > latest['MACD_signal']:
        macd_signal = "Bullish 📈"
    else:
        macd_signal = "Bearish 📉"

    # Bollinger Bands analysis
    if latest['close'] > latest['BB_upper']:
        bb_signal = "Above Upper Band (Overbought) ⚠️"
    elif latest['close'] < latest['BB_lower']:
        bb_signal = "Below Lower Band (Oversold) 🔄"
    else:
        bb_signal = "Within Bands ↔️"

    # Moving Averages analysis
    if latest['MA20'] > latest['MA50'] and latest['MA50'] > latest['MA200']:
        ma_signal = "Bullish Alignment 📈"
    elif latest['MA20'] < latest['MA50'] and latest['MA50'] < latest['MA200']:
        ma_signal = "Bearish Alignment 📉"
    else:
        ma_signal = "Mixed Signals ↔️"

    response = f"""
📊 **Technical Analysis Report for {asset.upper()}**
--------------------------
• **Current Price**: ${latest['close']:.2f}
• **24h Volume**: {latest['volume']:.2f} {asset.upper()}

**📈 Indicators:**
• **RSI (14)**: {latest['RSI']:.2f} - {rsi_signal}
• **MACD**: {macd_signal}
• **Bollinger Bands**: {bb_signal}
• **Moving Averages**: {ma_signal}

**📊 Key Levels:**
• **BB Upper**: ${latest['BB_upper']:.2f}
• **BB Middle**: ${latest['BB_middle']:.2f}
• **BB Lower**: ${latest['BB_lower']:.2f}
• **MA20**: ${latest['MA20']:.2f}
• **MA50**: ${latest['MA50']:.2f}
• **MA200**: ${latest['MA200']:.2f}

*Data from Binance • Generated at {datetime.now().strftime("%H:%M:%S")}*
"""
    return response


def get_trading_signal(asset="BTC"):
    symbol = f"{asset.upper()}/USDT"
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=100)

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # RSI
    rsi_indicator = RSIIndicator(close=df['close'], window=14)
    df['RSI'] = rsi_indicator.rsi()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    if latest['RSI'] < 35 and latest['close'] > prev['close']:
        direction = "BUY"
        color = "🟢"
        base_price = latest['close']
        entry_min = base_price * 0.995
        entry_max = base_price * 1.005
        target = base_price * 1.03
        stop_loss = base_price * 0.97
    elif latest['RSI'] > 65 and latest['close'] < prev['close']:
        direction = "SELL"
        color = "🔴"
        base_price = latest['close']
        entry_min = base_price * 0.995
        entry_max = base_price * 1.005
        target = base_price * 0.97
        stop_loss = base_price * 1.03
    else:
        direction = "HOLD"
        color = "🟡"
        base_price = latest['close']
        entry_min = base_price
        entry_max = base_price
        target = base_price
        stop_loss = base_price

    response = f"""
📈 **Trading Signal for {asset.upper()}**
--------------------------
{color} **{direction}** Recommendation
• **Current Price**: ${latest['close']:.2f}
• **RSI (14)**: {latest['RSI']:.2f}

**Entry**: ${entry_min:.2f} - ${entry_max:.2f}
**Target**: ${target:.2f}
**Stop Loss**: ${stop_loss:.2f}

*Data from Binance • Generated at {datetime.now().strftime("%H:%M:%S")}*
"""
    return response
