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
