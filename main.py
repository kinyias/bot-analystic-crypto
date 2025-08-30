import discord
from discord.ext import commands
from config import TOKEN
from services.analytic import get_technical_analysis, get_trading_signal
from flask import Flask, jsonify
import threading
import time

# Khởi tạo Flask app
app = Flask(__name__)
# Biến toàn cục để lưu trạng thái bot
bot_status = {
    "status": "Đang khởi động...",
    "start_time": time.time(),
    "commands_processed": 0
}
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
# Routes cho web server
@app.route('/')
def home():
    uptime = time.time() - bot_status["start_time"]
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"""
    <html>
        <head>
            <title>Discord Bot Status</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .status {{
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                }}
                .online {{
                    background-color: #d4edda;
                    color: #155724;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Discord Bot Status</h1>
                <div class="status online">
                    <strong>🟢 {bot_status['status']}</strong>
                </div>
                <p><strong>Thời gian hoạt động:</strong> {int(hours)} giờ, {int(minutes)} phút, {int(seconds)} giây</p>
                <p><strong>Số lệnh đã xử lý:</strong> {bot_status['commands_processed']}</p>
                <p><strong>Port đang chạy:</strong> 5000</p>
                <p><strong>Bot ID:</strong> {bot.user.id if bot.user else 'Chưa kết nối'}</p>
            </div>
        </body>
    </html>
    """

@app.route('/api/status')
def api_status():
    return jsonify(bot_status)

@app.route('/api/health')
def api_health():
    return jsonify({"status": "healthy", "bot_ready": bot.is_ready()})

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành công với tên {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

@bot.command()
async def analytic(ctx, asset="BTC"):
    try:
        response = get_technical_analysis(asset)
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def signal(ctx, asset="BTC"):
    try:
        response = get_trading_signal(asset)
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
if __name__ == "__main__":
    # Khởi chạy Flask server trong một thread riêng biệt
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
bot.run(TOKEN)
