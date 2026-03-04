"""
runner.py — Orchestrateur de la suite de tests API Yu-Gi-Oh!

Ce module :
1. Exécute séquentiellement les 6 tests fonctionnels définis dans `tester.tests`.
2. Calcule les métriques de QoS (passed, failed, error_rate, latence moyenne, P95).
3. Persiste le résultat complet dans la base SQLite via `storage`.
4. Retourne le dictionnaire normalisé du run.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, quantiles

# ── Ajustement du sys.path pour pouvoir importer storage (racine) et tester.tests ──
# La racine du projet est le parent du dossier `tester/`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import storage  # noqa: E402  — module à la racine du projet
from tester.tests import (  # noqa: E402
    test_status_200_known_card,
    test_content_type_json,
    test_required_fields,
    test_data_types,
    test_invalid_card_returns_error,
    test_banlist_tcg,
)

# Liste ordonnée de toutes les fonctions de test à exécuter
ALL_TESTS = [
    test_status_200_known_card,
    test_content_type_json,
    test_required_fields,
    test_data_types,
    test_invalid_card_returns_error,
    test_banlist_tcg,
]


def _compute_p95(latencies: list[float]) -> float:
    """
    Calcule le 95ème percentile d'une liste de latences.

    `statistics.quantiles` requiert au moins 2 valeurs pour découper
    en percentiles. Si la liste contient 0 ou 1 élément, on retourne
    directement la seule valeur disponible (ou 0.0).
    """
    if len(latencies) == 0:
        return 0.0
    if len(latencies) == 1:
        return latencies[0]
    # Découpage en 20 quantiles → l'indice 18 (19ème valeur) correspond au P95
    q = quantiles(latencies, n=20)
    return round(q[18], 2)  # index 18 = 95ème percentile


def execute_run() -> dict:
    """
    Orchestre un run complet :
      1. Exécute chaque test séquentiellement.
      2. Agrège les résultats et calcule les métriques de QoS.
      3. Initialise la base de données et persiste le run.
      4. Retourne le dictionnaire normalisé.

    Returns:
        Dictionnaire structuré selon le format convenu :
        {
            "api": "Yu-Gi-Oh!",
            "timestamp": "YYYY-MM-DDTHH:MM:SS",
            "summary": { passed, failed, error_rate, latency_ms_avg, latency_ms_p95 },
            "tests": [ ... ]
        }
    """
    # ── 1. Exécution des tests ──
    test_results: list[dict] = []
    for test_fn in ALL_TESTS:
        result = test_fn()
        test_results.append(result)

    # ── 2. Calcul des métriques de QoS ──
    total = len(test_results)
    passed = sum(1 for t in test_results if t["status"] == "PASS")
    failed = total - passed

    # Taux d'erreur arrondi à 4 décimales
    error_rate = round(failed / total, 4) if total > 0 else 0.0

    # Collecte des latences valides (certaines peuvent être None en cas d'erreur réseau)
    latencies = [
        t["latency_ms"] for t in test_results if t["latency_ms"] is not None
    ]

    # Latence moyenne (module statistics.mean)
    latency_ms_avg = round(mean(latencies), 2) if latencies else 0.0

    # 95ème percentile (module statistics.quantiles)
    latency_ms_p95 = _compute_p95(latencies)

    # ── 3. Construction du dictionnaire de run ──
    run_data = {
        "api": "Yu-Gi-Oh!",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "passed": passed,
            "failed": failed,
            "error_rate": error_rate,
            "latency_ms_avg": latency_ms_avg,
            "latency_ms_p95": latency_ms_p95,
        },
        "tests": test_results,
    }

    # ── 4. Persistance en base SQLite ──
    storage.init_db()       # création de la table si première exécution
    storage.save_run(run_data)  # insertion du run

    return run_data


# ======================================================================
# Point d'entrée — exécution directe
# ======================================================================
if __name__ == "__main__":
    import json as _json

    print("⏳  Exécution du run de tests…\n")
    run = execute_run()

    # Affichage formaté du résultat complet
    print(_json.dumps(run, indent=2, ensure_ascii=False))

    # Résumé rapide
    s = run["summary"]
    icon = "✅" if s["failed"] == 0 else "⚠️"
    print(f"\n{icon}  {s['passed']}/{s['passed'] + s['failed']} tests réussis  "
          f"| Latence moy. {s['latency_ms_avg']} ms  "
          f"| P95 {s['latency_ms_p95']} ms")
