import os
import sqlite3
from datetime import datetime
from datetime import date, timedelta

# ----------------------------------------------------------------------
# Chemins absolus (compatibles Railway, conteneur /app, et dev local)
# ----------------------------------------------------------------------
APP_DIR = os.environ.get("APP_DIR", "/app")

LAST_FETCH_PATH = os.path.join(APP_DIR, "last_fetch.txt")
DATABASE_DIR = os.path.join(APP_DIR, "database")
TACHES_DB_PATH = os.path.join(DATABASE_DIR, "taches.db")

# Chargement optionnel du .env en développement local
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_DIR, ".env"))
except Exception:
    pass

def doit_relancer_la_requete(chemin=LAST_FETCH_PATH, delai_jours=7):
    if not os.path.exists(chemin):
        return True
    with open(chemin, "r") as f:
        contenu = f.read().strip()
    try:
        derniere_date = date.fromisoformat(contenu)
    except ValueError:
        return True
    return (date.today() - derniere_date) >= timedelta(days=delai_jours)

def marquer_requete_effectuee(chemin=LAST_FETCH_PATH):
    with open(chemin, "w") as f:
        f.write(date.today().isoformat())

import sendRequester
if doit_relancer_la_requete():
    sendRequester.main()
    marquer_requete_effectuee()
else:
    print("Requête ADE ignorée : dernière mise à jour datant de moins d'une semaine.")

import parseEdtSQLite2
parseEdtSQLite2.mainL2()
parseEdtSQLite2.mainL1()
parseEdtSQLite2.mainL1InfoDiane()
parseEdtSQLite2.mainL1InfoSakyna()
parseEdtSQLite2.main1InfoLinda()
parseEdtSQLite2.main1InfoAndréa()

import DisplayConfig.DisplayConfigL2
DisplayConfig.DisplayConfigL2.main()

import DisplayConfig.DisplayConfigL1
DisplayConfig.DisplayConfigL1.main()

import DisplayConfig.DisplayConfigL1infoDiane
DisplayConfig.DisplayConfigL1infoDiane.main()

import DisplayConfig.DisplayConfigL1infoSakyna
DisplayConfig.DisplayConfigL1infoSakyna.main()

import DisplayConfig.DisplayConfigL1infoLinda
DisplayConfig.DisplayConfigL1infoLinda.main()

import DisplayConfig.DisplayConfigL1infoAndréa
DisplayConfig.DisplayConfigL1infoAndréa.main()

# ----------------------------------------------------------------------
# Configuration Pygame en mode headless (Railway = pas d'écran)
# ----------------------------------------------------------------------
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import io
import discord
from discord.ext import commands
import pygame

import edt_pygame as edt

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
# Token Discord lu depuis la variable d'environnement DISCORD_TOKEN.
# Sur Railway : ajouter DISCORD_TOKEN dans l'onglet "Variables".
# En local : mettre DISCORD_TOKEN=... dans le fichier .env à la racine.
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "La variable d'environnement DISCORD_TOKEN est absente. "
        "Ajoutez-la dans l'onglet Variables de Railway ou dans le fichier .env."
    )

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

pygame.init()
POLICE_JOUR = pygame.font.SysFont("arial", 18, bold=True)
POLICE_HEURE = pygame.font.SysFont("arial", 13)
POLICE_NOM = pygame.font.SysFont("arial", 14, bold=True)
POLICE_TITRE = pygame.font.SysFont("arial", 16, bold=True)

# ----------------------------------------------------------------------
# Génération de l'image
# ----------------------------------------------------------------------
async def spamMatt(ctx, nombre):
    await ctx.send("coucou @matt_off ")

def ajouter_tache_discord(nom_tache: str, date_fin: str, pseudo: str):
    """Ajoute une tâche depuis Discord."""
    connection = sqlite3.connect(TACHES_DB_PATH)
    cursor = connection.cursor()

    # Vérifier le format de la date (AAAA-MM-JJ)
    try:
        datetime.strptime(date_fin, "%Y-%m-%d")
    except ValueError:
        return False  # Format invalide

    cursor.execute(
        "INSERT INTO Tasks (nom, dateD, dateF, pseudo) VALUES (?, ?, ?, ?)",
        (nom_tache, datetime.now().strftime("%Y-%m-%d"), date_fin, pseudo)
    )
    connection.commit()
    connection.close()
    return True

def generer_image_semaine(offset_semaines=0):
    """
    Génère l'image PNG (en mémoire) de l'emploi du temps pour la semaine
    en cours + offset_semaines (0 = semaine actuelle, 1 = semaine suivante...).
    Renvoie (buffer_png, titre, nombre_de_cours).
    """
    edt.switchPath("L2")  # Par défaut, on charge L2 (à modifier selon la commande)
    cours_liste, lundi, dimanche = edt.charger_cours()

    largeur, hauteur = edt.LARGEUR_FENETRE, edt.HAUTEUR_FENETRE
    surface = pygame.Surface((largeur, hauteur))
    grille = edt.Grille(largeur, hauteur)

    titre = f"Semaine du {lundi.strftime('%d/%m/%Y')} au {dimanche.strftime('%d/%m/%Y')}"
    titre_surf = POLICE_TITRE.render(titre, True, edt.COULEUR_TEXTE)
    surface.fill(edt.COULEUR_FOND)
    surface.blit(titre_surf, (grille.zone_gauche, 10))

    edt.dessiner_grille(surface, grille, POLICE_HEURE, POLICE_JOUR)
    for cours in cours_liste:
        edt.dessiner_cours(surface, grille, cours, POLICE_NOM, POLICE_HEURE, False)

    buffer = io.BytesIO()
    pygame.image.save(surface, buffer, "PNG")
    buffer.seek(0)
    return buffer, titre, len(cours_liste)

async def envoyer_edt(ctx, offset_semaines=0):
    buffer, titre, nb_cours = generer_image_semaine(offset_semaines)

    if nb_cours == 0:
        await ctx.send(f"Aucun cours trouvé pour {titre}.")
        return

    fichier = discord.File(buffer, filename="edt.png")
    await ctx.send(f"**{titre}** — {nb_cours} cours :", file=fichier)

# ----------------------------------------------------------------------
# Commandes Discord
# ----------------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)
    else:
        await bot.process_commands(message)

    if (message.author.id == 859986955904565864):  # <- J'ai corrigé l'ID ici (exemple)
        await message.channel.send("coucou @matt_off ")

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

@bot.command(name="L2")
async def edt_command_l2(ctx, nombre: int = 0):
    edt.switchPath("L2")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="L1")
async def edt_command_l1(ctx, nombre: int = 0):
    edt.switchPath("L1")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="Diane")
async def edt_command_diane(ctx, nombre: int = 0):
    edt.switchPath("Diane")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="Sakyna")
async def edt_command_sakyna(ctx, nombre: int = 0):
    edt.switchPath("Sakyna")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="Linda")
async def edt_command_linda(ctx, nombre: int = 0):
    edt.switchPath("Linda")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="Andrea")
async def edt_command_andrea(ctx, nombre: int = 0):
    edt.switchPath("Andrea")
    await envoyer_edt(ctx, offset_semaines=nombre)

@bot.command(name="spam")
async def spam_command(ctx):
    """!spam -> Spamme 'ㅤㅤㅤ' 5 fois."""
    for _ in range(20):
        await ctx.send("ㅤㅤㅤ")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_command(ctx, nombre: int = 100):
    await ctx.channel.purge(limit=nombre + 1)

@bot.command(name="pdf")
async def pdfSend(ctx, type, theme):
    """envoie le pdf associer (!pdf cours/exo/corrigé theme)"""
    pdf_dir = os.path.join(APP_DIR, f"pdf{type}")
    pdf = discord.File(os.path.join(pdf_dir, f"{type}_{theme}.pdf"))
    await ctx.send(file=pdf)

@bot.command(name="tache")
async def ajouter_tache(ctx, *, args):
    """
    Commande pour ajouter une tâche :
    !tache [nom de la tâche] /date [AAAA-MM-JJ]

    Exemple :
    !tache Faire les courses /date 2026-09-20
    """
    try:
        # Parser les arguments
        if "/date" not in args:
            await ctx.send("Format : `!tache <nom> /date <AAAA-MM-JJ>`")
            return

        nom_tache, date_part = args.split("/date")
        nom_tache = nom_tache.strip()
        date_fin = date_part.strip()

        # Ajouter la tâche
        ok = ajouter_tache_discord(nom_tache, date_fin, ctx.author.name)
        if ok:
            await ctx.send(f"Tâche **{nom_tache}** ajoutée pour le {date_fin}.")
        else:
            await ctx.send("Date invalide. Format attendu : `AAAA-MM-JJ`.")
    except Exception as e:
        await ctx.send(f"Erreur : {str(e)}")

@bot.command(name="tache_effectuee")
async def marquer_effectuee(ctx, id_tache: int):
    """Marque une tâche comme effectuée."""
    connection = sqlite3.connect(TACHES_DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE Tasks SET effectuee = 1 WHERE id = ? AND pseudo = ?",
        (id_tache, ctx.author.name)
    )

    if cursor.rowcount == 0:
        await ctx.send("Tâche introuvable.")
    else:
        await ctx.send("Tâche marquée comme effectuée.")
    connection.commit()
    connection.close()

@bot.command(name="mes_taches")
async def lister_taches(ctx):
    """Affiche vos tâches en cours."""
    connection = sqlite3.connect(TACHES_DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, nom, dateF FROM Tasks WHERE pseudo = ? AND effectuee = 0 ORDER BY dateF",
        (ctx.author.name,)
    )
    taches = cursor.fetchall()
    connection.close()
    if not taches:
        await ctx.send("Vous n'avez aucune tâche en cours.")
        return
    message = "**Vos tâches :**\n"
    for tache in taches:
        message += f"#{tache[0]} — {tache[1]} (avant le {tache[2]})\n"
    await ctx.send(message)

bot.run(TOKEN)