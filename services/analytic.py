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

def get_trading_signal(asset="BTC/USDT",interval: str = "15m", model="deepseek/deepseek-chat-v3.1:free"):
    try:
        # Get technical data
        indicators = get_technical_analysis(asset,interval, is_signal=True)
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

*TRADING SIGNAL
- Provide a signal **only if multiple indicators align clearly** (e.g., RSI confirmation + MACD crossover + MA trend).
- If indicators conflict or show sideways movement → output **Neutral**.
- Signals: Strong Buy / Buy / Neutral / Sell / Strong Sell.

*RULES
- If Neutral → DO NOT provide entry/exit levels.
- If Buy/Sell → provide:
  1. Entry price range suggestion
  2. Stop-loss and take-profit levels
  3. Risk level (High/Medium/Low)
  4. Short-term outlook (Bullish/Bearish/Sideways)
  5. Key support/resistance levels to watch

Format clearly for Discord with sections and emojis.
Keep the output concise, no redundant explanations.
"""
        
        # Call AI API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
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

def get_trading_signal_max(asset="BTC/USDT",interval: str = "15m",model="deepseek/deepseek-chat-v3.1:free"):
    try:
        # Get technical data
        indicators = get_technical_analysis(asset,interval, is_signal=True)
        
        # Prepare technical context
        technical_context = f"""
CRYPTO TRADING SIGNAL ANALYSIS FOR {asset.upper()}

HERE IS DATA AND TECHNICAL INDICATORS:
{indicators}

*TRADING SIGNAL
- Provide a signal **only if multiple indicators align clearly** (e.g., RSI confirmation + MACD crossover + MA trend, volumn momentum).
- If indicators conflict or show sideways movement → output **Neutral**.
- Signals: Strong Buy / Buy / Neutral / Sell / Strong Sell.

*RULES
- If Neutral → DO NOT provide entry/exit levels.
- If Buy/Sell → provide:
  1. Entry price range suggestion
  2. Stop-loss and take-profit levels
  3. Risk level (High/Medium/Low)
  4. Short-term outlook (Bullish/Bearish/Sideways)
  5. Key support/resistance levels to watch

Format clearly for Discord with sections and emojis.
Keep the output concise, no redundant explanations.
"""
        
        # Call AI API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
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
    
def get_trading_signal_smc(asset="BTC/USDT",interval: str = "15m",model="deepseek/deepseek-chat-v3.1:free"):
    try:
        # Get technical data
        indicators = get_technical_analysis(asset,interval, is_signal=True)
        
        # Prepare technical context
        technical_context = f"""
* Analyze the current market data for {asset} using Smart Money Concept (SMC) to identify the highest-probability buy or sell opportunity that maximizes potential wins. Leverage SMC principles such as liquidity zones, order blocks (prioritized), breaker blocks, and fair value gaps to pinpoint institutional activity. Avoid trading during periods of extreme volatility.

* Incorporate the following additional rules to increase win probability:

- Confirmation with Volume Analysis: Ensure SMC signals (e.g., liquidity sweep, order block retest, or fair value gap) are confirmed by volume exceeding the 20-period average by at least 50%.
- Candlestick Patterns: Require confirmation from a bullish/bearish engulfing, pin bar, or inside bar at key SMC levels.
- Confluence with Key Levels: Ensure the signal aligns with major support/resistance, Fibonacci 61.8% retracement, or the 50/200 EMA.

* Provide the signal in this structured format:

🔹 Signal Type: [🟢Buy/🔴Sell/No Signal]
🔹 Entry Price: [Price]
🔹 Stop-Loss: [Price]
🔹 Take-Profit: [Price]
🔹 Confidence Level: [Low/Medium/High]
📌 Additional Notes: [Brief insight, e.g., 'Liquidity grab above recent high with volume spike' or 'Order block rejection confirmed by pin bar']

* Rules for Signal Generation:

- Prioritize the single most recent, high-confidence opportunity based on SMC principles, confirmed by clear institutional footprints (e.g., liquidity sweep reversing 1% within 3 candles, order block retest with volume and candlestick confirmation).
- Set Stop-Loss and Take-Profit based on SMC structure: Stop-Loss below/above the nearest SMC level (e.g., order block base, breaker block, or liquidity zone), and Take-Profit at the next logical SMC target (e.g., opposing liquidity zone, fair value gap fill, or breaker block retest), adjustable based on market context.
- Avoid multiple signals—focus on one actionable trade with the strongest setup.

* Only generate a response if:
- A new signal (Buy or Sell) differs from the previous signal (e.g., switches from Buy to Sell, Sell to Buy, or No Signal to Buy/Sell), or
- No prior signal exists, and a valid Buy, Sell, or No Signal is identified.
- If the current signal matches the previous signal, do not respond.
- If no valid opportunity meets the criteria (e.g., extreme volatility, unclear SMC levels, or insufficient volume), respond only with:
🔹 Signal Type: No Signal
🔹 Reason: [Brief explanation, e.g., 'Extreme volatility detected' or 'No clear SMC setup with volume confirmation']

* Important:

- Do not include additional text or explanations outside the structured format.
- If the signal is 'No Signal,' omit all other fields (e.g., Entry Price, Stop-Loss, Take-Profit, Confidence Level).
- Ensure the response is concise, data-driven, and adheres strictly to the format.
- Track the previous signal internally to compare with the current analysis, responding only when a change occurs or it’s the first signal.
HERE IS DATA {asset}:
{indicators}

"""
        
        # Call AI API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
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
