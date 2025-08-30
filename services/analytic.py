import ccxt
import pandas as pd
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from utils.formatter import format_discord_signal
from config import OPENROUTER_API_KEY
import requests
import json
# Binance exchange public data
exchange = ccxt.binance()

def get_technical_analysis(asset="BTC/USDT", interval="15m", is_signal=False):
    symbol = f"{asset.upper()}"
    ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=500)

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
• **RSI (24)**: {latest['RSI']:.2f} - {rsi_signal}
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
    if is_signal:
        return df
    else:
        return response


def get_trading_signal(asset="BTC/USDT"):
    try:
        # Get technical data
        indicators = get_technical_analysis(asset, is_signal=True)
        latest = indicators.iloc[-1]
        previous = indicators.iloc[-2]
        
        # Prepare technical context
        technical_context = f"""
CRYPTO TRADING SIGNAL ANALYSIS FOR {asset.upper()}

CURRENT PRICE: ${latest['close']:.2f}
24H VOLUME: {latest['volume']:.2f}

TECHNICAL INDICATORS:
- RSI: {latest['RSI']:.2f} ({'↑' if latest['RSI'] > previous['RSI'] else '↓'})
- MACD: {latest['MACD']:.6f}, Signal: {latest['MACD_signal']:.6f}
- Price Position: Between BB {latest['BB_lower']:.2f} - {latest['BB_upper']:.2f}
- MA Alignment: MA20: {latest['MA20']:.2f}, MA50: {latest['MA50']:.2f}, MA200: {latest['MA200']:.2f}

Provide a trading signal with:
1. Signal strength (Strong Buy/Buy/Neutral/Sell/Strong Sell)
2. Entry price suggestion
3. Stop-loss and take-profit levels
4. Risk level (High/Medium/Low)
5. Short-term outlook
6. Key levels to watch

Format for Discord with clear sections and relevant emojis.
"""
        
        # Call AI API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat-v3.1:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional crypto trading analyst. Provide clear, actionable trading signals with specific levels and risk assessment. Use Discord formatting with emojis and bullet points. Be concise but informative."
                    },
                    {
                        "role": "user",
                        "content": technical_context
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 600
            })
        )
        response_data = response.json()
        
        # Check if choices exists in response
        if 'choices' not in response_data:
            return f"❌ Unexpected API response format: {response_data}"
        
        if not response_data['choices']:
            return "❌ No response generated from AI"
        
        ai_response = response_data['choices'][0]['message']['content']
        
        # Format for Discord
        return format_discord_signal(asset, ai_response, indicators)
        
    except Exception as e:
        return f"❌ Error generating signal: {str(e)}"
