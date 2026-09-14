import sqlite3
import sys
import os
from datetime import date, timedelta

import pygame

# ----------------------------------------------------------------------
# Chemin absolu vers la base SQLite (compatible Railway / Docker)
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
    (231, 76, 60), (52, 152, 219), (46, 204, 113), (155, 89, 182),
    (241, 196, 15), (230, 126, 34), (26, 188, 156), (149, 165, 166),
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
        self.hauteur_grille = self.zone_bas - self.zone_haut

    def x_jour(self, jour):
        idx = JOURS.index(jour)
        return self.zone_gauche + idx * self.largeur_col

    def y_minute(self, minute_depuis_minuit):
        minute_relative = minute_depuis_minuit - HEURE_DEBUT * 60
        frac = minute_relative / self.minutes_totales
        return int(self.zone_haut + frac * self.hauteur_grille)

    def rect_cours(self, cours):
        x = self.x_jour(cours["jour"]) + 2
        y1 = self.y_minute(cours["debut"])
        y2 = self.y_minute(cours["fin"])
        largeur = self.largeur_col - 4
        hauteur = max(y2 - y1, 18)  # hauteur minimale pour rester lisible
        return pygame.Rect(x, y1, largeur, hauteur)

def dessiner_grille(ecran, grille, police_heure, police_jour):
    # Lignes verticales (heures)
    for h in range(HEURE_DEBUT, HEURE_FIN + 1):
        y = grille.y_minute(h * 60)
        pygame.draw.line(ecran, COULEUR_GRILLE, (grille.zone_gauche, y), (grille.zone_droite, y))
        label = police_heure.render(f"{h}h", True, COULEUR_TEXTE)
        ecran.blit(label, (grille.zone_gauche - label.get_width() - 8, y - label.get_height() / 2))

    # Lignes horizontales (jours)
    for i, jour in enumerate(JOURS):
        x = grille.zone_gauche + i * grille.largeur_col
        pygame.draw.line(ecran, COULEUR_GRILLE, (x, grille.zone_haut), (x, grille.zone_bas))

        # Entête du jour
        entete = pygame.Rect(x, grille.zone_haut - 40, grille.largeur_col, 40)
        pygame.draw.rect(ecran, COULEUR_ENTETE, entete)
        label = police_jour.render(jour, True, (255, 255, 255))
        ecran.blit(label, (x + grille.largeur_col / 2 - label.get_width() / 2,
                          grille.zone_haut - 40 + 10))

    # Bordure droite
    pygame.draw.line(ecran, COULEUR_GRILLE, (grille.zone_droite, grille.zone_haut),
                    (grille.zone_droite, grille.zone_bas))

def decouper_texte(texte, police, largeur_max):
    """Découpe un texte en plusieurs lignes pour qu'il tienne dans largeur_max."""
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

def dessiner_cours(ecran, grille, cours, police_nom, police_heure, survole):
    rect = grille.rect_cours(cours)
    couleur = couleur_pour(cours["nom"])
    if survole:
        couleur = tuple(min(255, c + 40) for c in couleur)

    pygame.draw.rect(ecran, couleur, rect, border_radius=6)
    pygame.draw.rect(ecran, (0, 0, 0), rect, width=1, border_radius=6)

    h1, m1 = divmod(cours["debut"], 60)
    h2, m2 = divmod(cours["fin"], 60)
    horaire = f"{h1:02d}h{m1:02d} - {h2:02d}h{m2:02d}"

    # Affichage du nom avec groupe
    nom_groupe = f"{cours['nom']} ({cours['groupe']})" if cours.get("groupe") else cours["nom"]
    nom_lignes = decouper_texte(nom_groupe, police_nom, rect.width - 8)
    y_offset = rect.y + 4
    for ligne in nom_lignes[:2]:  # Limite à 2 lignes max
        surf = police_nom.render(ligne, True, COULEUR_TEXTE_BLOC)
        ecran.blit(surf, (rect.x + 4, y_offset))
        y_offset += surf.get_height()

    # Affichage de la salle en bas
    if cours.get("salle"):
        salle_texte = f"📍 {cours['salle']}"
        salle_lignes = decouper_texte(salle_texte, police_nom, rect.width - 8)
        for ligne in salle_lignes[:1]:  # 1 ligne max pour la salle
            surf_salle = police_nom.render(ligne, True, COULEUR_TEXTE_BLOC)
            ecran.blit(surf_salle, (rect.x + 4, rect.bottom - surf_salle.get_height() - 2))

    # Affichage de l'horaire si espace disponible
    if rect.height > 40 and not cours.get("salle"):
        surf_h = police_heure.render(horaire, True, COULEUR_TEXTE_BLOC)
        ecran.blit(surf_h, (rect.x + 4, rect.bottom - surf_h.get_height() - 2))

    return rect

# Boucle principale
def main():
    global DB_PATH
    pygame.init()
    pygame.display.set_caption("Emploi du temps")

    ecran = pygame.display.set_mode((LARGEUR_FENETRE, HAUTEUR_FENETRE), pygame.RESIZABLE)
    horloge = pygame.time.Clock()

    # Polices
    police_jour = pygame.font.SysFont("arial", 18, bold=True)
    police_heure = pygame.font.SysFont("arial", 13)
    police_nom = pygame.font.SysFont("arial", 14, bold=True)
    police_info = pygame.font.SysFont("arial", 15)
    police_titre = pygame.font.SysFont("arial", 16, bold=True)

    # Chargement des cours
    cours_liste, lundi, dimanche = charger_cours()
    titre_semaine = f"Semaine du {lundi.strftime('%d/%m/%Y')} au {dimanche.strftime('%d/%m/%Y')}"
    pygame.display.set_caption(f"Emploi du temps - {titre_semaine}")

    if not cours_liste:
        print("Aucun cours trouvé pour cette semaine (ni la suivante).")

    largeur, hauteur = LARGEUR_FENETRE, HAUTEUR_FENETRE
    en_cours = True

    while en_cours:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                en_cours = False
            elif event.type == pygame.VIDEORESIZE:
                largeur, hauteur = event.w, event.h
                ecran = pygame.display.set_mode((largeur, hauteur), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                en_cours = False

        grille = Grille(largeur, hauteur)
        souris = pygame.mouse.get_pos()

        ecran.fill(COULEUR_FOND)

        # Titre de la semaine
        titre_surf = police_titre.render(titre_semaine, True, COULEUR_TEXTE)
        ecran.blit(titre_surf, (grille.zone_gauche, 10))

        # Dessin de la grille
        dessiner_grille(ecran, grille, police_heure, police_jour)

        # Dessin des cours
        bloc_survole = None
        for cours in cours_liste:
            rect = grille.rect_cours(cours)
            survole = rect.collidepoint(souris)
            dessiner_cours(ecran, grille, cours, police_nom, police_heure, survole)
            if survole:
                bloc_survole = cours

        # Infobulle au survol
        if bloc_survole:
            salle = f" | Salle: {bloc_survole.get('salle', '?')}" if bloc_survole.get("salle") else ""
            h1, m1 = divmod(bloc_survole["debut"], 60)
            h2, m2 = divmod(bloc_survole["fin"], 60)
            texte = f"{bloc_survole['nom']}  |  {bloc_survole['jour']}  {h1:02d}h{m1:02d}-{h2:02d}h{m2:02d}{salle}"
            surf = police_info.render(texte, True, (255, 255, 255))
            fond = pygame.Rect(souris[0] + 12, souris[1] + 12, surf.get_width() + 12, surf.get_height() + 8)
            pygame.draw.rect(ecran, (20, 20, 20), fond, border_radius=4)
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