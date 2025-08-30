from datetime import datetime
def format_analytic(asset, report):
    return f"""
    📊 **Analytic Report for {asset.upper()}**
    --------------------------
    • Market Trend: {report['trend']}
    • Volume: {report['volume']}
    • RSI: {report['rsi']}
    • Support Level: ${report['support']}
    • Resistance Level: ${report['resistance']}
    
    *Generated at {report['timestamp'].strftime("%H:%M:%S")}*
    """
def format_discord_signal(asset, ai_response, technical_data):
    latest = technical_data.iloc[-1]
    
    discord_message = f"""
🚨 **TRADING SIGNAL ALERT** 🚨
───────────────────────────────
**{asset.upper()}** • ${latest['close']:.2f}
📊 *Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}*

{ai_response}

📈 **TECHNICAL SNAPSHOT:**
• RSI: `{latest['RSI']:.2f}` {'🔴' if latest['RSI'] > 70 else '🟢' if latest['RSI'] < 30 else '🟡'}
• MACD: `{latest['MACD']:.4f}` {'📈' if latest['MACD'] > latest['MACD_signal'] else '📉'}
• BB Position: {'⚡ Overbought' if latest['close'] > latest['BB_upper'] else '💎 Oversold' if latest['close'] < latest['BB_lower'] else '🔄 Mid-Bands'}

🔔 **KEY LEVELS:**
• Support: `${latest['BB_lower']:.2f}` (BB Lower)
• Resistance: `${latest['BB_upper']:.2f}` (BB Upper)
• MA20: `${latest['MA20']:.2f}`
• MA50: `${latest['MA50']:.2f}`

⚠️ **RISK DISCLAIMER:** This is not financial advice. Always do your own research and trade responsibly.
"""
    return discord_message