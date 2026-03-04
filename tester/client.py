"""
client.py — Wrapper HTTP robuste pour monitorer une API.

Ce module fournit la classe `APIClient`, qui encapsule la librairie `requests`
avec gestion du timeout, du retry automatique, et des erreurs HTTP courantes
(429 Rate Limit, 5xx Server Error).
"""

import time
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


class APIClient:
    """
    Client HTTP réutilisable avec :
    - Timeout strict configurable (par défaut 3 s).
    - Mécanisme de retry (1 tentative supplémentaire en cas d'échec).
    - Gestion propre des erreurs 429 et 5xx.
    """

    def __init__(self, base_url: str, timeout: float = 3.0, max_retries: int = 1):
        """
        Initialise le client API.

        Args:
            base_url:     URL racine de l'API (sans slash final).
            timeout:      Délai maximum d'attente pour chaque requête (en secondes).
            max_retries:  Nombre de tentatives supplémentaires après un premier échec.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        # Session persistante : réutilise les connexions TCP (keep-alive)
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Méthode principale
    # ------------------------------------------------------------------
    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """
        Effectue une requête GET et retourne un dictionnaire normalisé.

        Returns:
            {
                "latency_ms":  float  — durée de la requête en millisecondes,
                "status_code": int | None — code HTTP reçu (None si aucune réponse),
                "json":        dict | list | None — corps JSON décodé,
                "error":       str | None — message d'erreur éventuel,
            }
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        attempt = 0
        last_error: str | None = None

        # Boucle de retry : tentative initiale + max_retries
        while attempt <= self.max_retries:
            attempt += 1
            try:
                # ── Envoi de la requête avec mesure de la latence ──
                start = time.perf_counter()
                response = self.session.get(url, params=params, timeout=self.timeout)
                latency_ms = (time.perf_counter() - start) * 1000

                # ── Gestion des codes HTTP spéciaux ──

                # 429 Too Many Requests : on attend le délai indiqué par le serveur
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    last_error = f"429 Rate Limit — Retry-After {retry_after}s"
                    time.sleep(retry_after)
                    continue  # relance la boucle

                # 5xx Server Error : on retente directement
                if 500 <= response.status_code < 600:
                    last_error = f"{response.status_code} Server Error"
                    continue  # relance la boucle

                # ── Tentative de décodage JSON ──
                try:
                    json_body = response.json()
                except ValueError:
                    json_body = None

                return {
                    "latency_ms": round(latency_ms, 2),
                    "status_code": response.status_code,
                    "json": json_body,
                    "error": None,
                    "headers": dict(response.headers),
                }

            except Timeout:
                last_error = f"Timeout après {self.timeout}s"
            except ConnectionError as exc:
                last_error = f"Erreur de connexion : {exc}"
            except RequestException as exc:
                last_error = f"Erreur HTTP générique : {exc}"

        # Toutes les tentatives ont échoué
        return {
            "latency_ms": None,
            "status_code": None,
            "json": None,
            "error": last_error,
            "headers": None,
        }

    def close(self):
        """Ferme la session HTTP sous-jacente."""
        self.session.close()

    # Support du context-manager (with APIClient(...) as c: ...)
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
