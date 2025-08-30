import discord
from discord.ext import commands
from config import TOKEN
from services.analytic import get_technical_analysis, get_trading_signal

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

bot.run(TOKEN)
