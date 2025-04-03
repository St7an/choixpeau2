import discord
from discord.ext import commands
from collections import defaultdict
import asyncio
import os
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# Rôles des maisons
HOUSE_ROLES = ["🦁gryffondor", "🐍Serpentard", "🦡Poufsouffle", "🦅Serdaigle"]

# Points attribués aux interactions
POINTS = {
    "reaction": 1,
    "message": 2,
    "vocal": 5,
    "event": 20,
    "quiz": 3,
    "invite": 15,
    "nitro": 50
}

# Charger les points depuis JSON
def load_points_from_json():
    if os.path.exists('points_data.json'):
        with open('points_data.json', 'r') as f:
            try:
                data = json.load(f)
                user_points = defaultdict(int, {int(k): v for k, v in data.get("user_points", {}).items()})
                house_points = data.get("house_points", {house: 0 for house in HOUSE_ROLES})
                return user_points, house_points
            except json.JSONDecodeError:
                print("Erreur lors de la lecture du fichier JSON. Réinitialisation des points.")
                return defaultdict(int), {house: 0 for house in HOUSE_ROLES}
    return defaultdict(int), {house: 0 for house in HOUSE_ROLES}

# Sauvegarder les points dans JSON
def save_points_to_json():
    data = {
        "user_points": dict(user_points),  # Convertir defaultdict en dict normal
        "house_points": house_points
    }
    with open('points_data.json', 'w') as f:
        json.dump(data, f, indent=4)

# Initialisation des points
user_points, house_points = load_points_from_json()

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")

# Attribution des points aux maisons
def update_house_points(user, points):
    for role in user.roles:
        if role.name in HOUSE_ROLES:
            house_points[role.name] += points
            print(f"{points} points ajoutés à la maison {role.name}")
            break

# Commande pour voir son solde
@bot.command()
async def solde(ctx, member: discord.Member = None):
    member = member or ctx.author
    points = user_points.get(member.id, 0)
    await ctx.send(f"{member.display_name} a {points} points.")

# Commande pour attribuer ou retirer des points
@bot.command()
async def points(ctx, amount: int, member: discord.Member):
    if not isinstance(amount, int):
        await ctx.send("Le montant doit être un nombre entier.")
        return

    if any(role.name in HOUSE_ROLES for role in member.roles):
        user_points[member.id] += amount
        update_house_points(member, amount)
        save_points_to_json()

        if amount > 0:
            await ctx.send(f"✅ {amount} points ont été **ajoutés** à {member.display_name} !")
        else:
            await ctx.send(f"❌ {abs(amount)} points ont été **retirés** à {member.display_name} !")
    else:
        await ctx.send(f"{member.display_name} ne fait pas partie d'une maison et ne peut pas gagner/perdre de points.")

# Commande pour réinitialiser les points
@bot.command()
async def retourneurdutemps(ctx):
    global user_points, house_points
    user_points.clear()
    house_points = {house: 0 for house in HOUSE_ROLES}
    save_points_to_json()
    await ctx.send("Tous les points ont été remis à zéro !")

# Commande pour mettre à jour les classements
@bot.command()
async def maj(ctx):
    guild = ctx.guild
    leaderboard_channel = discord.utils.get(guild.text_channels, name="🏆classements")
    if not leaderboard_channel:
        await ctx.send("Le salon **🏆classements** n'existe pas.")
        return
    
    sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_message = "\n".join([f"{guild.get_member(uid).display_name}: {pts} pts" for uid, pts in sorted_users if guild.get_member(uid)])
    sorted_houses = sorted(house_points.items(), key=lambda x: x[1], reverse=True)
    house_message = "\n".join([f"{house}: {pts} pts" for house, pts in sorted_houses])

    await leaderboard_channel.purge(limit=2)
    await leaderboard_channel.send(f"🏆 **Top 10 Membres** 🏆\n{leaderboard_message}")
    await leaderboard_channel.send(f"🏰 **Classement des Maisons** 🏰\n{house_message}")
    await ctx.send("Les classements ont été mis à jour.")

# Flask pour rendre le bot compatible avec Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot en ligne !"

def run_flask():
    port = os.getenv("PORT", 8080)  # Utiliser le port fourni par Render
    app.run(host='0.0.0.0', port=port)

# Lancer le bot Discord et Flask en même temps
async def start_bot_and_flask():
    from threading import Thread
    t = Thread(target=run_flask)
    t.start()
    await bot.start(TOKEN)

# Démarrer le bot
asyncio.run(start_bot_and_flask())
