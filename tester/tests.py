"""
tests.py — Suite de 6 tests fonctionnels pour l'API Yu-Gi-Oh!

Chaque fonction retourne un dictionnaire normalisé :
    {"name": str, "status": "PASS"|"FAIL", "latency_ms": float|None, "details": str}

API cible : https://db.ygoprodeck.com/api/v7/
"""

from tester.client import APIClient

# ── URL de base de l'API publique Yu-Gi-Oh! ──
BASE_URL = "https://db.ygoprodeck.com/api/v7"


def _result(name: str, passed: bool, latency_ms, details: str = "") -> dict:
    """Petit helper pour formater uniformément le résultat de chaque test."""
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "latency_ms": latency_ms,
        "details": details,
    }


# ======================================================================
# TEST 1 — HTTP 200 sur une carte existante
# ======================================================================
def test_status_200_known_card() -> dict:
    """
    Vérifie que l'endpoint `cardinfo.php` renvoie un code 200
    lorsqu'on demande une carte existante : "Red Dragon Archfiend".
    """
    name = "test_status_200_known_card"
    with APIClient(BASE_URL) as client:
        resp = client.get("cardinfo.php", params={"name": "Red Dragon Archfiend"})

    # Assertion : le code HTTP doit être exactement 200
    passed = resp["status_code"] == 200
    details = (
        "Code 200 reçu comme attendu."
        if passed
        else f"Code inattendu : {resp['status_code']} — {resp.get('error')}"
    )
    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# TEST 2 — Content-Type JSON sur randomcard
# ======================================================================
def test_content_type_json() -> dict:
    """
    Vérifie que l'endpoint `randomcard.php` renvoie bien un header
    Content-Type contenant 'application/json'.
    """
    name = "test_content_type_json"
    with APIClient(BASE_URL) as client:
        resp = client.get("randomcard.php")

    # Assertion : le Content-Type doit contenir "application/json"
    content_type = (resp.get("headers") or {}).get("Content-Type", "")
    passed = "application/json" in content_type
    details = (
        f"Content-Type correct : {content_type}"
        if passed
        else f"Content-Type inattendu : '{content_type}'"
    )
    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# TEST 3 — Présence des champs obligatoires (id, name, type)
# ======================================================================
def test_required_fields() -> dict:
    """
    Interroge une carte connue et vérifie que les champs 'id', 'name'
    et 'type' sont bien présents dans l'objet JSON retourné.
    """
    name = "test_required_fields"
    required_fields = {"id", "name", "type"}

    with APIClient(BASE_URL) as client:
        resp = client.get("cardinfo.php", params={"name": "Dark Magician"})

    if resp["status_code"] != 200 or resp["json"] is None:
        return _result(name, False, resp["latency_ms"],
                       f"Impossible de récupérer la carte (status={resp['status_code']})")

    # L'API retourne {"data": [{ ... }]} — on prend le premier résultat
    card = resp["json"].get("data", [{}])[0]

    # Assertion : chaque champ obligatoire doit être une clé du dict
    missing = required_fields - card.keys()
    passed = len(missing) == 0
    details = (
        f"Tous les champs obligatoires présents : {required_fields}"
        if passed
        else f"Champs manquants : {missing}"
    )
    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# TEST 4 — Vérification des types de données
# ======================================================================
def test_data_types() -> dict:
    """
    Vérifie que le champ 'id' est bien un entier (int) et que le champ
    'name' est bien une chaîne de caractères (str).
    """
    name = "test_data_types"

    with APIClient(BASE_URL) as client:
        resp = client.get("cardinfo.php", params={"name": "Blue-Eyes White Dragon"})

    if resp["status_code"] != 200 or resp["json"] is None:
        return _result(name, False, resp["latency_ms"],
                       f"Impossible de récupérer la carte (status={resp['status_code']})")

    card = resp["json"].get("data", [{}])[0]

    # Assertions typées
    id_ok = isinstance(card.get("id"), int)          # 'id' doit être un entier
    name_ok = isinstance(card.get("name"), str)       # 'name' doit être une chaîne

    passed = id_ok and name_ok
    details_parts = []
    if not id_ok:
        details_parts.append(f"'id' n'est pas int (type={type(card.get('id')).__name__})")
    if not name_ok:
        details_parts.append(f"'name' n'est pas str (type={type(card.get('name')).__name__})")
    details = "Types corrects (id=int, name=str)." if passed else " | ".join(details_parts)

    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# TEST 5 — Robustesse : carte inexistante → 400 (ou absence de "data")
# ======================================================================
def test_invalid_card_returns_error() -> dict:
    """
    Interroge `cardinfo.php` avec un nom de carte volontairement invalide.
    L'API Yu-Gi-Oh! doit répondre avec un statut HTTP **non-200**
    (généralement 400) pour signaler l'erreur.
    """
    name = "test_invalid_card_returns_error"
    fake_card = "CarteQuiNexistePas"

    with APIClient(BASE_URL) as client:
        resp = client.get("cardinfo.php", params={"name": fake_card})

    # Assertion : on s'attend strictement à un code 400
    # L'API renvoie {"error": "No card matching your query was found..."} avec 400
    passed = resp["status_code"] == 400
    details = (
        f"Code 400 reçu comme attendu pour la carte fictive '{fake_card}'."
        if passed
        else f"Code inattendu : {resp['status_code']} (attendu : 400)"
    )
    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# TEST 6 — Banlist TCG disponible
# ======================================================================
def test_banlist_tcg() -> dict:
    """
    Vérifie que l'endpoint `cardinfo.php?banlist=tcg` répond correctement
    (HTTP 200) et retourne une liste de cartes non vide.
    """
    name = "test_banlist_tcg"

    with APIClient(BASE_URL) as client:
        resp = client.get("cardinfo.php", params={"banlist": "tcg"})

    if resp["status_code"] != 200 or resp["json"] is None:
        return _result(name, False, resp["latency_ms"],
                       f"Endpoint banlist indisponible (status={resp['status_code']})")

    cards = resp["json"].get("data", [])

    # Assertion : la liste de cartes bannies/limitées ne doit pas être vide
    passed = len(cards) > 0
    details = (
        f"Banlist TCG disponible — {len(cards)} carte(s) retournée(s)."
        if passed
        else "La banlist TCG est vide."
    )
    return _result(name, passed, resp["latency_ms"], details)


# ======================================================================
# Point d'entrée — exécution de toute la suite de tests
# ======================================================================
if __name__ == "__main__":
    tests = [
        test_status_200_known_card,
        test_content_type_json,
        test_required_fields,
        test_data_types,
        test_invalid_card_returns_error,
        test_banlist_tcg,
    ]

    print("=" * 65)
    print("  SUITE DE TESTS — API Yu-Gi-Oh! (Testing as Code)")
    print("=" * 65)

    total, passed_count = len(tests), 0
    for test_fn in tests:
        result = test_fn()
        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"\n{status_icon}  {result['name']}")
        print(f"    Status  : {result['status']}")
        print(f"    Latence : {result['latency_ms']} ms")
        print(f"    Détails : {result['details']}")
        if result["status"] == "PASS":
            passed_count += 1

    print("\n" + "=" * 65)
    print(f"  RÉSULTAT : {passed_count}/{total} tests réussis")
    print("=" * 65)
