# Portfolio

Personal portfolio site. React + TypeScript (Vite) frontend, FastAPI + SQL backend.

## Run it

One command (starts both servers, Ctrl+C stops them):

```sh
./run.sh
```

Then open http://localhost:5173

### Or run the two pieces manually

Backend (terminal 1):

```sh
cd backend
uv run uvicorn app.main:app --port 8000
```

Frontend (terminal 2):

```sh
cd frontend
npm run dev
```

The frontend proxies `/api` to the backend on port 8000, so start the backend first.

> **Node version:** this needs Node 18+. If `node --version` shows an old version
> (e.g. v14), run `export PATH="/opt/homebrew/bin:$PATH"` first; that's what
> `run.sh` does automatically.

## Structure

- `frontend/`: React + TypeScript + Vite + Tailwind. Edit `src/config.ts` for
  all personal info (name, bio, links); projects and their case studies come
  from the API.
- `backend/`: FastAPI + SQLModel + SQLite. Serves `/api/projects` and
  `/api/contact`; seeds project content on first run (`app/seed.py`).

## Edit your content

- **Personal info / bio / social links:** `frontend/src/config.ts`
- **Projects & case studies:** `backend/app/seed.py` (delete `backend/data/portfolio.db`
  to re-seed after changing it)
