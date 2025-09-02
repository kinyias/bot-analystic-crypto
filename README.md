# 🤖 Crypto Trading Analysis Discord Bot

A powerful Discord bot that provides real-time cryptocurrency technical analysis and trading signals using multiple strategies including traditional indicators and Smart Money Concepts (SMC).

## 🌟 Features

- **Technical Analysis**: RSI, MACD, Bollinger Bands, and Moving Averages
- **AI-Powered Trading Signals**: Integration with OpenRouter AI models
- **Multiple Signal Types**:
  - Basic trading signals (`!signal`)
  - Advanced trading signals (`!asignal`)
  - Smart Money Concept signals (`!smcsignal`)
- **Web API**: Built-in Flask server with status endpoints
- **Discord Integration**: Easy-to-use commands with formatted responses

## 📋 Prerequisites

- Python 3.8+
- A Discord bot token (from Discord Developer Portal)
- An OpenRouter API key (from https://openrouter.ai/)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kinyias/bot-analystic-crypto.git
   cd bot-analystic-crypto
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

1. Create a `.env` file in the root directory based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your credentials:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

## ▶️ Usage

Run the bot with:
```bash
python main.py
```

The bot will start and connect to Discord, while also launching a web server on port 5000.

## 🎮 Commands

- `!ping` - Check if the bot is running
- `!analytic <asset> <interval>` - Perform technical analysis for a trading pair
  - Example: `!analytic BTC/USDT 1h`
- `!signal <asset> <interval> <model>` - Basic trading signal
  - Example: `!signal ETH/USDT 30m`
- `!asignal <asset> <interval> <model>` - Advanced trading signal
  - Example: `!asignal ADA/USDT 1h`
- `!smcsignal <asset> <interval> <model>` - SMC (Smart Money Concept) trading signal
  - Example: `!smcsignal XRP/USDT 4h`
- `!bothelp` - Display this help guide

### Parameters
- `<asset>`: Trading pair (default: BTC/USDT)
- `<interval>`: Timeframe (default: 15m)
- `<model>`: AI model (default: deepseek/deepseek-chat-v3.1:free)

## 🌐 Web API Endpoints

The bot includes a Flask web server running on port 5000 with the following endpoints:

- `GET /` - Web dashboard showing bot status
- `GET /api/status` - JSON response with bot status information
- `GET /api/health` - Health check endpoint

## 📦 Dependencies

- `ccxt==4.5.2` - Cryptocurrency trading library
- `discord.py==2.6.2` - Discord API wrapper
- `pandas==2.3.2` - Data analysis library
- `ta==0.11.0` - Technical analysis indicators
- `python-decouple==3.8` - Configuration management
- `Flask==3.1.2` - Web framework
- `requests==2.32.5` - HTTP library

## 📚 Technical Analysis Indicators

The bot uses several technical indicators for market analysis:
- **RSI (Relative Strength Index)**: Momentum indicator that measures the speed and change of price movements
- **MACD (Moving Average Convergence Divergence)**: Trend-following momentum indicator
- **Bollinger Bands**: Volatility bands placed above and below a moving average
- **Moving Averages**: EMA indicators for 20, 50, and 200 periods

## ⚠️ Disclaimer

This bot is for educational purposes only. The trading signals provided should not be considered financial advice. Always do your own research and trade responsibly. Cryptocurrency trading involves substantial risk of loss.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
