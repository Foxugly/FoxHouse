# FoxHouse

Site de jeux de cartes de la flotte Foxugly : API Django (`backend/`) et frontend Angular (`frontend/`).
Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.

## Développement

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
$env:DJANGO_DEBUG="True"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m ruff check .
```

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
