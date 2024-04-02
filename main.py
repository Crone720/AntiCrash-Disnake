import os

import disnake
from disnake.ext import commands

intents = disnake.Intents.all()
bot = commands.Bot(
    command_prefix="1", 
    intents=disnake.Intents.all(), 
    help_command=None,
    reload=True
)
for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")

@bot.event
async def on_ready():
    print(f'Бот запустился')
    
bot.run("token")