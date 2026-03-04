"""
storage.py — Persistance des résultats de tests dans une base SQLite.

Ce module fournit les fonctions nécessaires pour :
- Initialiser la base de données `monitoring.db` et sa table `runs`.
- Sauvegarder le résultat complet d'un run de tests.
- Récupérer les derniers runs sous forme de liste de dictionnaires.
"""

import json
import sqlite3
from pathlib import Path

# Chemin de la base de données, placée à la racine du projet
DB_PATH = Path(__file__).resolve().parent / "monitoring.db"


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion à la base SQLite avec row_factory pour obtenir des dicts."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # permet d'accéder aux colonnes par nom
    return conn


# ======================================================================
# Initialisation de la base de données
# ======================================================================
def init_db() -> None:
    """
    Crée la base `monitoring.db` et la table `runs` si elle n'existe pas encore.

    Colonnes de la table `runs` :
        - id              : clé primaire auto-incrémentée
        - timestamp       : date/heure du run (format ISO 8601)
        - passed          : nombre de tests réussis
        - failed          : nombre de tests échoués
        - error_rate      : taux d'erreur (failed / total)
        - latency_avg     : latence moyenne en ms
        - latency_p95     : 95ème percentile des latences en ms
        - raw_tests_json  : résultat complet du run sérialisé en JSON
    """
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                passed          INTEGER NOT NULL,
                failed          INTEGER NOT NULL,
                error_rate      REAL    NOT NULL,
                latency_avg     REAL    NOT NULL,
                latency_p95     REAL    NOT NULL,
                raw_tests_json  TEXT    NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ======================================================================
# Sauvegarde d'un run
# ======================================================================
def save_run(run_data: dict) -> None:
    """
    Insère un run complet dans la table `runs`.

    Args:
        run_data: dictionnaire issu de `runner.execute_run()`, contenant
                  au minimum les clés 'timestamp', 'summary' et 'tests'.
    """
    summary = run_data["summary"]
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO runs (timestamp, passed, failed, error_rate,
                              latency_avg, latency_p95, raw_tests_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_data["timestamp"],
                summary["passed"],
                summary["failed"],
                summary["error_rate"],
                summary["latency_ms_avg"],
                summary["latency_ms_p95"],
                json.dumps(run_data, ensure_ascii=False),  # sérialisation complète
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ======================================================================
# Récupération des derniers runs
# ======================================================================
def get_latest_runs(limit: int = 10) -> list[dict]:
    """
    Retourne les *limit* derniers runs, du plus récent au plus ancien.

    Chaque élément est un dictionnaire avec les colonnes de la table `runs`.
    Le champ `raw_tests_json` est automatiquement désérialisé en objet Python.

    Args:
        limit: nombre maximum de runs à retourner (par défaut 10).

    Returns:
        Liste de dictionnaires représentant les runs.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        row_dict = dict(row)
        # Désérialiser le JSON brut pour le rendre exploitable
        try:
            row_dict["raw_tests_json"] = json.loads(row_dict["raw_tests_json"])
        except (json.JSONDecodeError, TypeError):
            pass  # on garde la chaîne telle quelle en cas d'erreur
        results.append(row_dict)

    return results
