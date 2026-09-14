import re
import sqlite3
import sys

DB_PATH = "./database/edtDatabaseL2.db"

MATIERES_A_MASQUER = [
    "Modélisation",
    "Algèbre 2",
    "Résolution de problèmes et oral",
    "Outils Mathématiques et Complexité",
    "Méthodes numériques 1",
]

GROUPES_CHOISIS = {
    "CM-MAT31": "CM-MAT31",
    "CM-INF35": "CM-INF35",
    "CM-INF32": "CM-INF32",
    "CM-MAT33": "CM-MAT33",
    "CM-MAT34": "CM-MAT34",
    "CM-INF37": "CM-INF37",
    "TD-INF31": "TD-INF31 Groupe-01",
    "TP-INF37": "TP-INF37 Groupe-A",
    "TD-MAT3": "TD-MAT3- Groupe A",
    "TD-MAT32": "TD-MAT32 - Groupe A",
    "TD-MAT33": "TD-MAT33- Groupe A",
    "TD-INF32": "TD-INF32 Groupe-01",
    "TP-INF35": "TP-INF35 Groupe-A",
    "TD-MAT35": "TD-MAT35",
    "TD-MAT34": "TD-MAT34- Groupe A",
    "TP-INF31": "TP-INF31 Groupe-A"
}

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def code_de_base(groupe):
    """
    Extrait le code de base d'un champ groupe, ex:
    "TP-INF37 Groupe-A" -> "TP-INF37"
    "TD-MAT3- Groupe A"  -> "TD-MAT3" (supprime le tiret à la fin)
    "TD-MAT35"           -> "TD-MAT35" (pas de groupe multiple)
    """
    if not groupe:
        return groupe
    code = re.split(r"\s*-?\s*Groupe", groupe, flags=re.IGNORECASE)[0].strip()
    # Supprime les tirets à la fin (ex: "TD-MAT3-" -> "TD-MAT3")
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