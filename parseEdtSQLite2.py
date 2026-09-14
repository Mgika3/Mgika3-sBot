import re
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FUSEAU_PARIS = ZoneInfo("Europe/Paris")
MOTIF_CODE_COURS = re.compile(r"^[A-Z0-9\-]+$")

# ---------------------------------------------------------------------------
# Partie 1 : Parsing du fichier ICS
# ---------------------------------------------------------------------------

def unfold_lines(raw_text):
    """
    Recolle les lignes repliées du format iCalendar.
    Une ligne de continuation commence par un espace ou une tabulation.
    """
    raw_lines = raw_text.splitlines()
    unfolded = []
    for line in raw_lines:
        if line.startswith(" ") or line.startswith("\t"):
            if unfolded:
                unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded

def parse_ics(path):
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    lines = unfold_lines(raw_text)

    events = []
    current = {}
    in_event = False

    for line in lines:
        if line.startswith("BEGIN:VEVENT"):
            in_event = True
            current = {}
        elif line.startswith("END:VEVENT"):
            if current:
                events.append(current)
            in_event = False
        elif in_event and ":" in line:
            cle, _, valeur = line.partition(":")
            current[cle.strip()] = valeur.strip()

    return events

def parse_datetime(valeur):
    """
    Convertit une date iCal type 20261113T134500Z (UTC) en objet datetime
    exprimé en heure locale française (gère automatiquement CET/CEST).
    """
    est_utc = valeur.endswith("Z")
    valeur_propre = valeur.rstrip("Z")
    dt = datetime.strptime(valeur_propre, "%Y%m%dT%H%M%S")
    if est_utc:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(FUSEAU_PARIS)
    return dt

def parse_description(description):
    """
    Extrait la matière et le prof depuis le champ DESCRIPTION.

    IMPORTANT : le nombre de lignes de la DESCRIPTION varie selon les cours
    (certains ont une ligne de sous-thème en plus, ex: Outils mathématiques
    -> Algèbre/Analyse, ou un intitulé de séance à la place du prof, ex:
    "Certification PIX", "Séance à la BU"). Se fier à la POSITION des lignes
    pour trouver le groupe est donc fragile et a été source de bugs.

    -> La matière est fiable en position 0 (toujours la première ligne).
    -> Le vrai code de groupe est récupéré depuis SUMMARY (voir
       construire_liste_tuples), jamais depuis DESCRIPTION.
    -> Le prof, quand présent, est la dernière ligne utile avant la mention
       "(Exporté le:...)".
    """
    texte = description.strip()
    texte = re.sub(r"\\n\(Export.*?\)\\n?$", "", texte)
    parties = [p for p in texte.split("\\n") if p != ""]

    matiere = parties[0] if len(parties) > 0 else ""
    prof = parties[-1] if len(parties) > 1 else ""

    return matiere, prof

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def construire_liste_tuples(events):
    """
    Construit la liste de tuples au format attendu par la table CoursMaths :
    (nom, jour, heureD, minD, heureF, minF, display, date, groupe, salle)

    Le champ "groupe" est désormais le SUMMARY brut de l'événement ICS
    (ex: "TD-INF16 Groupe-02", "CM-INF11"), qui est la seule source fiable
    et cohérente du code de groupe, quel que soit le nombre de lignes dans
    DESCRIPTION.
    """
    resultats = []

    for e in events:
        if "DTSTART" not in e or "DTEND" not in e:
            continue

        dtstart = parse_datetime(e["DTSTART"])
        dtend = parse_datetime(e["DTEND"])
        matiere, prof = parse_description(e.get("DESCRIPTION", ""))
        resume = e.get("SUMMARY", "")
        salle = e.get("LOCATION", "")

        if matiere and not MOTIF_CODE_COURS.match(matiere):
            nom = matiere
        else:
            nom = resume or matiere

        groupe = resume  # SUMMARY = code de groupe fiable

        jour = JOURS_FR[dtstart.weekday()]

        tup = (
            nom,                        # nom
            jour,                       # jour
            dtstart.hour,               # heureD
            dtstart.minute,             # minD
            dtend.hour,                 # heureF
            dtend.minute,               # minF
            True,                       # display
            dtstart.date().isoformat(), # date (YYYY-MM-DD)
            groupe,                     # groupe (= SUMMARY)
            salle,                      # salle
        )
        resultats.append(tup)

    return resultats

# ---------------------------------------------------------------------------
# Partie 2 : Insertion en base SQLite
# ---------------------------------------------------------------------------

listeCours = []

def fillList(listeTuple):
    global listeCours
    listeCours = listeTuple

def _inserer(db_path):
    connextion = sqlite3.connect(db_path)
    curseur = connextion.cursor()

    curseur.execute("""
        CREATE TABLE IF NOT EXISTS CoursMaths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            jour TEXT NOT NULL,
            heureD INTEGER,
            minD INTEGER,   
            heureF INTEGER,
            minF INTEGER,
            display BOOLEAN,
            date TEXT,
            groupe TEXT,
            salle TEXT
        )
    """)
    connextion.commit()

    curseur.execute("DELETE FROM CoursMaths")
    curseur.executemany(
        "INSERT INTO CoursMaths (nom, jour, heureD, minD, heureF, minF, display, date, groupe, salle) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        listeCours
    )
    connextion.commit()
    connextion.close()

def main2():
    _inserer("./database/edtDatabaseL2.db")

def main1():
    _inserer("./database/edtDatabaseL1.db")

def main1InfoDiane():
    _inserer("./database/edtDatabaseL1InfoDiane.db")

def main1InfoLinda():
    _inserer("./database/edtDatabaseL1InfoLinda.db")

def main1InfoSakyna():
    _inserer("./database/edtDatabaseL1InfoSakyna.db")

def main1InfoAndréa():
    _inserer("./database/edtDatabaseL1InfoAndrea.db")


def _traiter(nom_fichier_ics, inserer_fn, db_path):
    events = parse_ics(nom_fichier_ics)
    tuples = construire_liste_tuples(events)

    print(f"{len(tuples)} cours prêts à être insérés.")

    fillList(tuples)
    inserer_fn()

    connextion = sqlite3.connect(db_path)
    curseur = connextion.cursor()
    curseur.execute("SELECT * FROM CoursMaths")
    resultat = curseur.fetchall()
    print(f"{len(resultat)} lignes dans la base ({db_path}).")
    connextion.close()

def mainL2():
    _traiter("./ADE/ADECalL2.ics", main2, "./database/edtDatabaseL2.db")

def mainL1():
    _traiter("./ADE/ADECalL1.ics", main1, "./database/edtDatabaseL1.db")

def mainL1InfoDiane():
    _traiter("./ADE/ADECalL1.ics", main1InfoDiane, "./database/edtDatabaseL1InfoDiane.db")

def mainL1InfoSakyna():
    _traiter("./ADE/ADECalL1.ics", main1InfoSakyna, "./database/edtDatabaseL1InfoSakyna.db")

def mainL1InfoLinda():
    _traiter("./ADE/ADECalL1.ics", main1InfoLinda, "./database/edtDatabaseL1InfoLinda.db")

def mainL1InfoAndrea():
    _traiter("./ADE/ADECalL1.ics", main1InfoAndréa, "./database/edtDatabaseL1InfoAndrea.db")


