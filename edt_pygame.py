import sqlite3
import sys
import os
from datetime import date, timedelta

import pygame

# ----------------------------------------------------------------------
# Chemin absolu vers la base SQLite (compatible Railway / Docker)
# En développement local on peut surcharger APP_DIR via l'environnement.
# ----------------------------------------------------------------------
APP_DIR = os.environ.get("APP_DIR", "/app")
DATABASE_DIR = os.path.join(APP_DIR, "database")
ADE_DIR = os.path.join(APP_DIR, "ADE")

DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL2.db")

# Configuration
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

HEURE_DEBUT = 8    # 8h
HEURE_FIN = 20     # 20h

LARGEUR_FENETRE = 1200
HAUTEUR_FENETRE = 750

MARGE_GAUCHE = 70
MARGE_HAUT = 85
MARGE_DROITE = 20
MARGE_BAS = 20

COULEUR_FOND = (255, 255, 255)
COULEUR_GRILLE = (200, 200, 200)
COULEUR_TEXTE = (30, 30, 30)
COULEUR_TEXTE_BLOC = (255, 255, 255)
COULEUR_ENTETE = (60, 90, 150)

PALETTE = [
    (220, 90, 90),    # rouge
    (90, 170, 220),   # bleu
    (130, 200, 110),  # vert
    (240, 180, 70),   # jaune
    (180, 120, 200),  # violet
    (200, 130, 90),   # orange/brun
    (110, 200, 200),  # cyan
    (200, 100, 170),  # rose
    (150, 150, 150),  # gris
]

# Chargement des données
JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def lundi_de_la_semaine(jour_ref):
    return jour_ref - timedelta(days=jour_ref.weekday())

def charger_cours_periode(db_path, debut, fin):
    try:
        connexion = sqlite3.connect(db_path)
        curseur = connexion.cursor()
        curseur.execute(
            """
            SELECT nom, jour, heureD, minD, heureF, minF, date, groupe, salle
            FROM CoursMaths
            WHERE display=1 AND date BETWEEN ? AND ?
            """,
            (debut.isoformat(), fin.isoformat()),
        )
        rows = curseur.fetchall()
        connexion.close()
    except sqlite3.OperationalError as e:
        print(f"[edt_pygame] Erreur SQLite ({db_path}) : {e}")
        return []

    cours = []
    for row in rows:
        nom, jour, heureD, minD, heureF, minF, jour_date, groupe, salle = row
        if jour not in JOURS:
            continue
        cours.append({
            "nom": nom.strip() if nom else "?",
            "jour": jour,
            "debut": int(heureD) * 60 + int(minD),
            "fin": int(heureF) * 60 + int(minF),
            "date": jour_date,
            "groupe": groupe.strip() if groupe else "",
            "salle": salle.strip() if salle else "",
        })
    return cours

def charger_cours(db_path=DB_PATH):
    """
    Charge les cours de la semaine en cours ; si elle est vide, bascule
    sur la semaine suivante.
    """
    aujourdhui = date.today()
    lundi = lundi_de_la_semaine(aujourdhui)
    dimanche = lundi + timedelta(days=6)

    cours = charger_cours_periode(db_path, lundi, dimanche)

    if not cours:
        lundi = lundi + timedelta(weeks=1)
        dimanche = lundi + timedelta(days=6)
        cours = charger_cours_periode(db_path, lundi, dimanche)

    return cours, lundi, dimanche

def couleur_pour(nom):
    return PALETTE[hash(nom) % len(PALETTE)]

# Géométrie de la grille
class Grille:
    def __init__(self, largeur_fenetre, hauteur_fenetre):
        self.largeur_fenetre = largeur_fenetre
        self.hauteur_fenetre = hauteur_fenetre
        self.zone_gauche = MARGE_GAUCHE
        self.zone_haut = MARGE_HAUT
        self.zone_droite = largeur_fenetre - MARGE_DROITE
        self.zone_bas = hauteur_fenetre - MARGE_BAS
        self.largeur_col = (self.zone_droite - self.zone_gauche) / len(JOURS)
        self.minutes_totales = (HEURE_FIN - HEURE_DEBUT) * 60
        self.hauteur_totale = self.zone_bas - self.zone_haut

    def x_jour(self, jour):
        idx = JOURS.index(jour)
        return self.zone_gauche + idx * self.largeur_col

    def y_minute(self, minute_depuis_minuit):
        minute_relative = minute_depuis_minuit - HEURE_DEBUT * 60
        frac = minute_relative / self.minutes_totales
        return int(self.zone_haut + frac * self.hauteur_totale)

    def rect_cours(self, cours):
        x = self.x_jour(cours["jour"]) + 2
        y1 = self.y_minute(cours["debut"])
        y2 = self.y_minute(cours["fin"])
        largeur = self.largeur_col - 4
        hauteur = max(1, y2 - y1)
        return pygame.Rect(x, y1, largeur, hauteur)


def dessiner_grille(ecran, grille):
    for h in range(HEURE_DEBUT, HEURE_FIN + 1):
        y = grille.y_minute(h * 60)
        pygame.draw.line(ecran, COULEUR_GRILLE, (grille.zone_gauche, y), (grille.zone_droite, y))

    for i, jour in enumerate(JOURS):
        x = grille.zone_gauche + i * grille.largeur_col
        pygame.draw.line(ecran, COULEUR_GRILLE, (x, grille.zone_haut), (x, grille.zone_bas))
        entete = pygame.Rect(int(x), 0, int(grille.largeur_col), MARGE_HAUT - 5)
        pygame.draw.rect(ecran, COULEUR_ENTETE, entete)
        surf = pygame.font.SysFont("arial", 14, bold=True).render(jour, True, (255, 255, 255))
        ecran.blit(surf, (x + 6, 6))


def dessiner_cours(ecran, grille, cours, survole=False):
    rect = grille.rect_cours(cours)
    couleur = couleur_pour(cours["nom"])
    if survole:
        couleur = tuple(min(255, c + 30) for c in couleur)
    pygame.draw.rect(ecran, couleur, rect)
    pygame.draw.rect(ecran, (0, 0, 0), rect, 1)

    h1, m1 = divmod(cours["debut"], 60)
    h2, m2 = divmod(cours["fin"], 60)
    horaire = f"{h1:02d}h{m1:02d} - {h2:02d}h{m2:02d}"

    surf_horaire = pygame.font.SysFont("arial", 11).render(horaire, True, COULEUR_TEXTE_BLOC)
    surf_nom = POLICE_NOM.render(cours["nom"], True, COULEUR_TEXTE_BLOC) if False else pygame.font.SysFont("arial", 13, bold=True).render(cours["nom"], True, COULEUR_TEXTE_BLOC)

    y_offset = rect.y + 4
    ecran.blit(surf_horaire, (rect.x + 4, y_offset))
    y_offset += surf_horaire.get_height()
    ecran.blit(surf_nom, (rect.x + 4, y_offset))
    y_offset += surf_nom.get_height()

    if cours.get("salle"):
        salle_texte = f"📍 {cours['salle']}"
        surf_salle = pygame.font.SysFont("arial", 11).render(salle_texte, True, COULEUR_TEXTE_BLOC)
        ecran.blit(surf_salle, (rect.x + 4, y_offset))

    return rect


def decouper_texte(texte, police, largeur_max):
    mots = texte.split()
    lignes = []
    ligne_courante = ""
    for mot in mots:
        essai = f"{ligne_courante} {mot}".strip()
        if police.size(essai)[0] <= largeur_max:
            ligne_courante = essai
        else:
            if ligne_courante:
                lignes.append(ligne_courante)
            ligne_courante = mot
    if ligne_courante:
        lignes.append(ligne_courante)
    return lignes or [""]


# Boucle principale (uniquement pour debug local — sur Railway le bot
# utilise generer_image_semaine() / dessiner_grille() / dessiner_cours()).
def main():
    global DB_PATH
    pygame.init()
    pygame.display.set_caption("Emploi du temps")
    ecran = pygame.display.set_mode((LARGEUR_FENETRE, HAUTEUR_FENETRE), pygame.RESIZABLE)
    horloge = pygame.time.Clock()

    police_heure = pygame.font.SysFont("arial", 13)
    police_info = pygame.font.SysFont("arial", 15)

    cours_liste, lundi, dimanche = charger_cours()
    if not cours_liste:
        print("Aucun cours à afficher.")
        return

    largeur, hauteur = LARGEUR_FENETRE, HAUTEUR_FENETRE
    en_cours = True

    while en_cours:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                en_cours = False
            elif event.type == pygame.VIDEORESIZE:
                largeur, hauteur = event.w, event.h
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                en_cours = False

        grille = Grille(largeur, hauteur)
        souris = pygame.mouse.get_pos()

        ecran.fill(COULEUR_FOND)
        dessiner_grille(ecran, grille)

        bloc_survole = None
        rects_dessines = []
        for cours in cours_liste:
            rect = dessiner_cours(ecran, grille, cours, survole=False)
            rects_dessines.append((rect, cours))
            survole = rect.collidepoint(souris)
            if survole:
                bloc_survole = cours

        if bloc_survole:
            h1, m1 = divmod(bloc_survole["debut"], 60)
            h2, m2 = divmod(bloc_survole["fin"], 60)
            surf = police_info.render(f"{h1:02d}h{m1:02d}-{h2:02d}h{m2:02d} — {bloc_survole['nom']}", True, COULEUR_TEXTE)
            fond = pygame.Rect(souris[0] + 10, souris[1] + 10, surf.get_width() + 12, surf.get_height() + 8)
            pygame.draw.rect(ecran, (255, 255, 220), fond)
            ecran.blit(surf, (fond.x + 6, fond.y + 4))

        pygame.display.flip()
        horloge.tick(60)

    pygame.quit()
    sys.exit()

def switchPath(licence):
    global DB_PATH
    if licence == "L1":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL1.db")
    elif licence == "L2":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL2.db")
    elif licence == "Diane":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL1InfoDiane.db")
    elif licence == "Sakyna":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL1InfoSakyna.db")
    elif licence == "Linda":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL1InfoLinda.db")
    elif licence == "Andrea":
        DB_PATH = os.path.join(DATABASE_DIR, "edtDatabaseL1InfoAndrea.db")


if __name__ == "__main__":
    main()
