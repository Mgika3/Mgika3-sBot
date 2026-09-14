import re
import sqlite3
import sys

DB_PATH = "./database/edtDatabaseL1InfoAndrea.db"

MATIERES_A_MASQUER = [
    "Analyse 1",
    "Algèbre linéaire 1",
    "Pratique du calcul mathématiques",
    "Programmation Python",
    "Raisonnement et ensembles",
    "Tableur",
    "Logiciel de présentation",
    "Traitement de texte"
    
]

GROUPES_CHOISIS = {
    "CM-INF11" : "CM-INF11",
    "CM-INF12" : "CM-INF12",
    "CM-INF15" : "CM-INF15",
    "TD-INF17" : "TD-INF17 Groupe-01",
    "TD-INF11" : "TD-INF11 Groupe-01",
    "TD-INF16" : "TD-INF16 Groupe-01",
    "TD-INF14" : "TD-INF14 Groupe-01",
    "TP-INF14" : "TP-INF14 Groupe-A",
    "TD-INF12" : "TD-INF12 Groupe-01",
    "TP-INF15" : "TP-INF15 Groupe-B",
    "TD-INF13" : "TD-INF13 Groupe-02"

}

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def code_de_base(groupe):
    if not groupe:
        return groupe
    code = re.split(r"\s*-?\s*Groupe", groupe, flags=re.IGNORECASE)[0].strip()
    return code.rstrip("-")

# ---------------------------------------------------------------------------
# Fonctions principales
# ---------------------------------------------------------------------------

def lister():
    """Affiche toutes les matières et groupes présents dans la base."""
    connexion = sqlite3.connect(DB_PATH)
    curseur = connexion.cursor()
    curseur.execute("SELECT DISTINCT nom, groupe FROM CoursMaths ORDER BY nom, groupe")
    lignes = curseur.fetchall()
    connexion.close()

    print(f"{'MATIERE':45s} | GROUPE")
    print("-" * 90)
    for nom, groupe in lignes:
        print(f"{nom[:45]:45s} | {groupe}")

def appliquer():
    """Met à jour la colonne 'display' dans la base selon MATIERES_A_MASQUER et GROUPES_CHOISIS."""
    connexion = sqlite3.connect(DB_PATH)
    curseur = connexion.cursor()
    curseur.execute("SELECT id, nom, groupe FROM CoursMaths")
    lignes = curseur.fetchall()

    nb_affiches = 0
    nb_masques = 0
    mises_a_jour = []

    for id_, nom, groupe in lignes:
        garder = True

        if nom in MATIERES_A_MASQUER:
            garder = False
        else:
            base = code_de_base(groupe)
            if base in GROUPES_CHOISIS:
                if groupe != GROUPES_CHOISIS[base]:
                    garder = False
            else:
                garder = False

        mises_a_jour.append((garder, id_))
        if garder:
            nb_affiches += 1
        else:
            nb_masques += 1

    # Appliquer les mises à jour
    curseur.executemany("UPDATE CoursMaths SET display = ? WHERE id = ?", mises_a_jour)
    connexion.commit()
    connexion.close()

    print(f"✅ {nb_affiches} cours affichés, {nb_masques} cours masqués.")

# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    appliquer()