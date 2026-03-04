"""
flask_app.py — Application Web Flask pour le monitoring d'API Yu-Gi-Oh!

Routes :
    /           → redirige vers /dashboard
    /run        → déclenche un run de tests et retourne le JSON
    /dashboard  → tableau de bord visuel (dernier run + historique)
    /health     → health-check du service
    /consignes  → page de consignes de l'atelier (existante)
"""

from flask import Flask, render_template, jsonify, redirect, url_for

import storage
from tester import runner

# ── Initialisation de l'application Flask ──
app = Flask(__name__)

# Création de la base de données au démarrage (idempotent)
storage.init_db()


# ======================================================================
# Route : /  →  redirection vers le dashboard
# ======================================================================
@app.route("/")
def index():
    """Redirige automatiquement l'utilisateur vers le tableau de bord."""
    return redirect(url_for("dashboard"))


# ======================================================================
# Route : /run  →  exécution d'un nouveau run de tests
# ======================================================================
@app.route("/run")
def run_tests():
    """
    Déclenche un run complet des 6 tests via l'orchestrateur,
    puis retourne le résultat en JSON.
    """
    result = runner.execute_run()
    return jsonify(result)


# ======================================================================
# Route : /dashboard  →  tableau de bord visuel
# ======================================================================
@app.route("/dashboard")
def dashboard():
    """
    Récupère l'historique des runs depuis la base SQLite et rend
    le template dashboard.html.

    Si aucun run n'existe encore, le template recevra `latest=None`
    pour pouvoir afficher un message adapté.
    """
    runs = storage.get_latest_runs(limit=20)

    if not runs:
        # Aucun test n'a encore été lancé
        return render_template("dashboard.html", latest=None, history=[])

    # Le premier élément est le run le plus récent (ORDER BY id DESC)
    latest = runs[0]
    history = runs  # on passe tout l'historique (y compris le dernier)

    return render_template("dashboard.html", latest=latest, history=history)


# ======================================================================
# Route : /health  →  health-check
# ======================================================================
@app.route("/health")
def health():
    """Retourne un simple indicateur de santé du service."""
    return jsonify({"status": "healthy", "service": "Monitoring API"}), 200


# ======================================================================
# Route : /consignes  →  page de consignes de l'atelier
# ======================================================================
@app.route("/consignes")
def consignes():
    """Affiche la page de consignes HTML."""
    return render_template("consignes.html")


# ======================================================================
# Point d'entrée
# ======================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
