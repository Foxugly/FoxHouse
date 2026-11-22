# FoxHouse

Site de jeux de cartes de la flotte Foxugly : API Django (`backend/`) et frontend Angular (`frontend/`).
Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.

## Développement

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.in -r requirements-dev.txt
$env:DJANGO_DEBUG="True"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m ruff check .
```

Dépendances : les directes (plages) sont dans `backend/requirements.in` ; `backend/requirements.txt` est un
**verrou haché** généré par uv pour Linux / Python 3.14 (la production), installé tel quel au déploiement
(`--require-hashes --no-deps`, puis `pip check`). Après une modification de `requirements.in`, régénérer le
verrou avec la commande de son en-tête (`uv pip compile requirements.in --generate-hashes --python-version 3.14
--python-platform x86_64-unknown-linux-gnu -o requirements.txt`). Sous Linux (CI), installer en deux temps :
`pip install --require-hashes -r requirements.txt` puis `pip install -r requirements-dev.txt` (une seule ligne
hachée fait passer pip en mode hashes pour toute l'installation). **Sous Windows le verrou ne s'installe pas**
(il n'a pas `tzdata`, dépendance de Django propre à Windows) : d'où `requirements.in` ci-dessus.

Frontend (Node 24) :

```powershell
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Jouer en local : lancer `manage.py runserver` dans `backend/` (avec `DJANGO_DEBUG=True`), puis
`npm start` dans `frontend/` et ouvrir http://localhost:4200 (le proxy renvoie `/api` vers le port 8000).
Captures d'écran : `docs/captures/`.
