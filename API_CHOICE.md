# API Choice

- Étudiant : Sofiane Chelghoum
- API choisie : Yu-Gi-Oh! API (YGOPRODeck)
- URL base : https://db.ygoprodeck.com/api/v7/
- Documentation officielle / README : https://ygoprodeck.com/api-guide/
- Auth : None
- Endpoints testés :
  - GET /cardinfo.php?name=Red%20Dragon%20Archfiend (Recherche précise)
  - GET /randomcard.php (Carte aléatoire)
  - GET /cardinfo.php?banlist=tcg (Liste filtrée)
  - GET /cardinfo.php?name=CarteQuiNexistePas (Test d'erreur 400)
- Hypothèses de contrat (champs attendus, types, codes) :
  - Le Content-Type doit être `application/json`.
  - Le code HTTP attendu est 200 (ou 400 pour les erreurs provoquées).
  - La structure de données d'une carte doit contenir les clés `id` (entier), `name` (chaîne de caractères), et `type` (chaîne de caractères).
- Limites / rate limiting connu : 20 requêtes par seconde maximum.
- Risques (instabilité, downtime, CORS, etc.) : Risque de recevoir une erreur 429 si la limite de requêtes est dépassée, ou une erreur 5xx en cas de maintenance des serveurs de la base de données YGOPRODeck.