import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange
from utils.formatter import format_discord_signal
from config import OPENROUTER_API_KEY
import requests
import json

# Binance exchange public data
exchange = ccxt.binance()

def calculate_supertrend(df, period=10, multiplier=3.0):
    """Calculate Supertrend indicator"""
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period).average_true_range()
    
    hl2 = (df['high'] + df['low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(len(df)):
        if i == 0:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = 1
        else:
            # Calculate basic upper and lower bands
            if upper_band.iloc[i] < supertrend.iloc[i-1] or df['close'].iloc[i-1] > supertrend.iloc[i-1]:
                upper_band.iloc[i] = upper_band.iloc[i]
            else:
                upper_band.iloc[i] = supertrend.iloc[i-1]
                
            if lower_band.iloc[i] > supertrend.iloc[i-1] or df['close'].iloc[i-1] < supertrend.iloc[i-1]:
                lower_band.iloc[i] = lower_band.iloc[i]
            else:
                lower_band.iloc[i] = supertrend.iloc[i-1]
            
            # Determine supertrend direction
            if df['close'].iloc[i] <= lower_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = -1
            elif df['close'].iloc[i] >= upper_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]
    
    return supertrend, direction

def resample_to_higher_timeframe(df, htf='4H'):
    """Resample data to higher timeframe"""
    # Reset index to make timestamp a column for resampling
    df_reset = df.reset_index()
    df_reset.set_index('timestamp', inplace=True)
    
    # Resample to higher timeframe
    htf_data = df_reset.resample(htf).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return htf_data

def get_advanced_technical_analysis(asset="BTC/USDT", interval="15m", 
                                  fast_ema=21, slow_ema=55, rsi_length=14, 
                                  rsi_long_threshold=55, rsi_short_threshold=45,
                                  supertrend_period=10, supertrend_multiplier=3.0,
                                  atr_length=14, atr_sma_length=14, r_multiple=2.0,
                                  htf_interval='4H', htf_ema_length=50):
    """
    Advanced technical analysis with EMA Cloud, Supertrend, and multi-filter strategy
    """
    try:
        symbol = f"{asset.upper()}"
        
        # Get more data for higher timeframe analysis
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=1000)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # 1. EMA Cloud
        df['fast_ema'] = EMAIndicator(close=df['close'], window=fast_ema).ema_indicator().fillna(df['close'])
        df['slow_ema'] = EMAIndicator(close=df['close'], window=slow_ema).ema_indicator().fillna(df['close'])
        
        # 2. Supertrend
        df['supertrend'], df['supertrend_direction'] = calculate_supertrend(
            df, period=supertrend_period, multiplier=supertrend_multiplier
        )
        
        # 3. RSI
        df['rsi'] = RSIIndicator(close=df['close'], window=rsi_length).rsi()
        
        # 4. MACD
        macd_indicator = MACD(close=df['close'])
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_histogram'] = macd_indicator.macd_diff()
        
        # 5. Volatility Filter (ATR)
        df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=atr_length).average_true_range()
        df['atr_sma'] = df['atr'].rolling(window=atr_sma_length).mean()
        
        # 6. Higher Timeframe Confirmation
        try:
            htf_data = resample_to_higher_timeframe(df, htf_interval)
            htf_data['htf_ema'] = EMAIndicator(close=htf_data['close'], window=htf_ema_length).ema_indicator()
            
            # Align HTF EMA with LTF data (forward fill)
            df = df.join(htf_data[['htf_ema']], how='left')
            df['htf_ema'] = df['htf_ema'].fillna(method='ffill')
        except Exception as e:
            print(f"HTF analysis error: {e}")
            df['htf_ema'] = df['close']  # Fallback
        
        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 2 else previous
        
        # Analyze conditions
        analysis = analyze_trading_conditions(df, current, previous, prev2, 
                                            rsi_long_threshold, rsi_short_threshold, r_multiple)
        
        return df, analysis
        
    except Exception as e:
        return None, f"Error in technical analysis: {str(e)}"

def analyze_trading_conditions(df, current, previous, prev2, 
                             rsi_long_threshold, rsi_short_threshold, r_multiple):
    """Analyze all trading conditions and generate signals"""
    
    analysis = {
        'signal': 'No Signal',
        'entry_price': None,
        'stop_loss': None,
        'take_profit': None,
        'confidence': 'Low',
        'details': {}
    }
    
    # 1. EMA Cloud Trend Analysis
    ema_trend = 'neutral'
    if (current['close'] > current['fast_ema'] and 
        current['close'] > current['slow_ema'] and 
        current['fast_ema'] > current['slow_ema']):
        ema_trend = 'bullish'
    elif (current['close'] < current['fast_ema'] and 
          current['close'] < current['slow_ema'] and 
          current['fast_ema'] < current['slow_ema']):
        ema_trend = 'bearish'
    
    analysis['details']['ema_trend'] = ema_trend
    
    # 2. RSI Filter
    rsi_allows_long = current['rsi'] > rsi_long_threshold
    rsi_allows_short = current['rsi'] < rsi_short_threshold
    
    analysis['details']['rsi'] = current['rsi']
    analysis['details']['rsi_allows_long'] = rsi_allows_long
    analysis['details']['rsi_allows_short'] = rsi_allows_short
    
    # 3. MACD Histogram Filter
    macd_allows_long = current['macd_histogram'] > 0
    macd_allows_short = current['macd_histogram'] < 0
    
    analysis['details']['macd_histogram'] = current['macd_histogram']
    analysis['details']['macd_allows_long'] = macd_allows_long
    analysis['details']['macd_allows_short'] = macd_allows_short
    
    # 4. Volatility Filter
    volatility_filter = current['atr'] > current['atr_sma']
    
    analysis['details']['volatility_filter'] = volatility_filter
    analysis['details']['atr'] = current['atr']
    analysis['details']['atr_sma'] = current['atr_sma']
    
    # 5. Higher Timeframe Filter
    htf_allows_long = current['close'] > current['htf_ema']
    htf_allows_short = current['close'] < current['htf_ema']
    
    analysis['details']['htf_allows_long'] = htf_allows_long
    analysis['details']['htf_allows_short'] = htf_allows_short
    
    # 6. Entry Triggers
    # EMA Cross
    ema_cross_bullish = (current['fast_ema'] > current['slow_ema'] and 
                        previous['fast_ema'] <= previous['slow_ema'])
    ema_cross_bearish = (current['fast_ema'] < current['slow_ema'] and 
                        previous['fast_ema'] >= previous['slow_ema'])
    
    # MACD Histogram Cross Zero
    macd_cross_bullish = (current['macd_histogram'] > 0 and previous['macd_histogram'] <= 0)
    macd_cross_bearish = (current['macd_histogram'] < 0 and previous['macd_histogram'] >= 0)
    
    # Price Cross Supertrend
    price_cross_st_bullish = (current['close'] > current['supertrend'] and 
                             previous['close'] <= previous['supertrend'])
    price_cross_st_bearish = (current['close'] < current['supertrend'] and 
                             previous['close'] >= previous['supertrend'])
    
    # Check for triggers
    bullish_trigger = ema_cross_bullish or macd_cross_bullish or price_cross_st_bullish
    bearish_trigger = ema_cross_bearish or macd_cross_bearish or price_cross_st_bearish
    
    analysis['details']['triggers'] = {
        'ema_cross_bullish': ema_cross_bullish,
        'ema_cross_bearish': ema_cross_bearish,
        'macd_cross_bullish': macd_cross_bullish,
        'macd_cross_bearish': macd_cross_bearish,
        'price_cross_st_bullish': price_cross_st_bullish,
        'price_cross_st_bearish': price_cross_st_bearish
    }
    
    # 7. Final Signal Generation
    # Long Signal Conditions
    if (bullish_trigger and ema_trend == 'bullish' and 
        rsi_allows_long and macd_allows_long and 
        volatility_filter and htf_allows_long):
        
        analysis['signal'] = 'Buy'
        analysis['entry_price'] = current['close']
        analysis['stop_loss'] = current['supertrend']
        analysis['take_profit'] = current['close'] + (current['atr'] * r_multiple)
        
        # Calculate confidence based on number of aligned factors
        confidence_factors = sum([
            ema_cross_bullish, macd_cross_bullish, price_cross_st_bullish,
            current['rsi'] > 60, current['macd_histogram'] > previous['macd_histogram']
        ])
        
        if confidence_factors >= 3:
            analysis['confidence'] = 'High'
        elif confidence_factors >= 2:
            analysis['confidence'] = 'Medium'
        else:
            analysis['confidence'] = 'Low'
    
    # Short Signal Conditions
    elif (bearish_trigger and ema_trend == 'bearish' and 
          rsi_allows_short and macd_allows_short and 
          volatility_filter and htf_allows_short):
        
        analysis['signal'] = 'Sell'
        analysis['entry_price'] = current['close']
        analysis['stop_loss'] = current['supertrend']
        analysis['take_profit'] = current['close'] - (current['atr'] * r_multiple)
        
        # Calculate confidence based on number of aligned factors
        confidence_factors = sum([
            ema_cross_bearish, macd_cross_bearish, price_cross_st_bearish,
            current['rsi'] < 40, current['macd_histogram'] < previous['macd_histogram']
        ])
        
        if confidence_factors >= 3:
            analysis['confidence'] = 'High'
        elif confidence_factors >= 2:
            analysis['confidence'] = 'Medium'
        else:
            analysis['confidence'] = 'Low'
    
    return analysis

def get_advanced_trading_signal(asset="BTC/USDT", interval="15m", 
                               model="deepseek/deepseek-chat-v3.1:free", **kwargs):
    """
    Generate advanced trading signals using multi-filter strategy
    """
    try:
        # Get technical analysis
        df, analysis = get_advanced_technical_analysis(asset, interval, **kwargs)
        
        if df is None:
            return f"❌ Error: {analysis}"
        
        current = df.iloc[-1]
        
        # Format the response
        if analysis['signal'] == 'No Signal':
            response = f"""
🔍 **Advanced Signal Analysis for {asset.upper()}**
--------------------------
📊 **Current Price**: ${current['close']:.2f}
🎯 **Signal**: {analysis['signal']}
📈 **Confidence**: {analysis['confidence']}

**📋 Filter Status:**
• **EMA Trend**: {analysis['details']['ema_trend'].title()} {'✅' if analysis['details']['ema_trend'] != 'neutral' else '⚠️'}
• **RSI Filter**: {current['rsi']:.1f} {'✅ Long OK' if analysis['details']['rsi_allows_long'] else '✅ Short OK' if analysis['details']['rsi_allows_short'] else '❌'}
• **MACD**: {analysis['details']['macd_histogram']:.4f} {'✅' if abs(analysis['details']['macd_histogram']) > 0.001 else '⚠️'}
• **Volatility**: {'✅ Active' if analysis['details']['volatility_filter'] else '❌ Low'}
• **HTF Trend**: {'✅ Bullish' if analysis['details']['htf_allows_long'] else '✅ Bearish' if analysis['details']['htf_allows_short'] else '⚠️'}

**🎯 Key Levels:**
• **Supertrend**: ${current['supertrend']:.2f}
• **Fast EMA**: ${current['fast_ema']:.2f}
• **Slow EMA**: ${current['slow_ema']:.2f}

*Waiting for trigger alignment • {datetime.now().strftime("%H:%M:%S")}*
"""
        else:
            # Calculate risk/reward
            if analysis['signal'] == 'Buy':
                risk = analysis['entry_price'] - analysis['stop_loss']
                reward = analysis['take_profit'] - analysis['entry_price']
            else:
                risk = analysis['stop_loss'] - analysis['entry_price']
                reward = analysis['entry_price'] - analysis['take_profit']
            
            rr_ratio = reward / risk if risk > 0 else 0
            
            response = f"""
🚨 **ADVANCED TRADING SIGNAL - {asset.upper()}**
--------------------------
🎯 **Signal**: {'🟢 ' + analysis['signal'].upper() if analysis['signal'] == 'Buy' else '🔴 ' + analysis['signal'].upper()}
📊 **Confidence**: {analysis['confidence']} {'🔥' if analysis['confidence'] == 'High' else '⚡' if analysis['confidence'] == 'Medium' else '💫'}

**📈 Trade Setup:**
• **Entry**: ${analysis['entry_price']:.2f}
• **Stop Loss**: ${analysis['stop_loss']:.2f}
• **Take Profit**: ${analysis['take_profit']:.2f}
• **Risk/Reward**: 1:{rr_ratio:.2f}

**✅ Confirmed Filters:**
• **EMA Cloud**: {analysis['details']['ema_trend'].title()} Trend
• **RSI**: {current['rsi']:.1f} - {'Long Zone' if analysis['details']['rsi_allows_long'] else 'Short Zone'}
• **MACD Histogram**: {analysis['details']['macd_histogram']:.4f}
• **Volatility**: Active (ATR > SMA)
• **HTF Confirmation**: Aligned

**🎯 Current Levels:**
• **Price**: ${current['close']:.2f}
• **Supertrend**: ${current['supertrend']:.2f}
• **ATR**: ${current['atr']:.2f}

*Multi-filter strategy activated • {datetime.now().strftime("%H:%M:%S")}*
"""
        
        return response
        
    except Exception as e:
        return f"❌ Error generating advanced signal: {str(e)}"

def get_advanced_trading_signal_ai(asset="BTC/USDT", interval="15m", 
                                  model="deepseek/deepseek-chat-v3.1:free", **kwargs):
    """
    Generate AI-enhanced advanced trading signals
    """
    try:
        # Get technical analysis
        df, analysis = get_advanced_technical_analysis(asset, interval, **kwargs)
        
        if df is None:
            return f"❌ Error: {analysis}"
        
        current = df.iloc[-1]
        entry_price_str = f"${analysis['entry_price']:.2f}" if analysis['entry_price'] else "N/A"
        stop_loss_str = f"${analysis['stop_loss']:.2f}" if analysis['stop_loss'] else "N/A"
        take_profit_str = f"${analysis['take_profit']:.2f}" if analysis['take_profit'] else "N/A"

        # Prepare context for AI
        technical_context = f"""
ADVANCED MULTI-FILTER TRADING ANALYSIS FOR {asset.upper()}

CURRENT MARKET DATA:
- Price: ${current['close']:.2f}
- Signal Generated: {analysis['signal']}
- Confidence Level: {analysis['confidence']}

FILTER STATUS:
- EMA Cloud Trend: {analysis['details']['ema_trend']}
- RSI ({current['rsi']:.1f}): Long OK={analysis['details']['rsi_allows_long']}, Short OK={analysis['details']['rsi_allows_short']}
- MACD Histogram: {analysis['details']['macd_histogram']:.4f}
- Volatility Filter: {analysis['details']['volatility_filter']}
- Higher Timeframe: Long OK={analysis['details']['htf_allows_long']}, Short OK={analysis['details']['htf_allows_short']}

TRIGGER ANALYSIS:
{analysis['details']['triggers']}

KEY LEVELS:
- Entry: {entry_price_str}
- Stop Loss: {stop_loss_str} (Supertrend: ${current['supertrend']:.2f})
- Take Profit: {take_profit_str}

INSTRUCTIONS:
- Validate the signal logic and provide professional analysis
- If signal exists, confirm entry/exit levels and add market context
- If no signal, explain what's missing for a valid setup
- Use Discord formatting with clear sections and emojis
- Keep analysis concise but comprehensive
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
                        "content": "You are an expert crypto trader specializing in multi-filter technical analysis. Provide clear, actionable insights using EMA Cloud, Supertrend, RSI, MACD, volatility, and higher timeframe analysis. Use Discord formatting with emojis."
                    },
                    {
                        "role": "user",
                        "content": technical_context
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 800
            })
        )
        
        response_data = response.json()
        
        if 'choices' not in response_data or not response_data['choices']:
            return f"❌ AI API error: {response_data}"
        
        ai_response = response_data['choices'][0]['message']['content']
        
        # Format for Discord (assuming format_discord_signal handles this)
        MAX_DISCORD_LENGTH = 1900  # safe buffer under 2000 chars

        ai_response_trimmed = ai_response
        if len(ai_response) > MAX_DISCORD_LENGTH:
            ai_response_trimmed = ai_response[:MAX_DISCORD_LENGTH] + "\n... (truncated)"
        return ai_response_trimmed
        
    except Exception as e:
        return f"❌ Error generating AI-enhanced signal: {str(e)}"