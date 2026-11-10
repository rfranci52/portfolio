# rakimfrancis.com

**Live: [www.rakimfrancis.com](https://www.rakimfrancis.com)**

My portfolio site: a React and TypeScript front end on Vercel, Python serverless functions, Neon Postgres, and a chatbot that answers questions from the case studies I wrote. The project pages are baked into the deployed bundle, so they need no server. The live natural-language-to-SQL (Structured Query Language) demo it links to is a separate repository, [nl-to-sql](https://github.com/rfranci52/nl-to-sql).

## The chatbot

A visitor asks a question and gets an answer drawn from my written case studies, with its sources listed and the model, cost and response time shown beneath it. The [How this works](https://www.rakimfrancis.com/how-this-works) page walks through the full path of a question. In short:

- **Limits come first.** By default each visitor gets 10 questions a day, the whole site gets 40, and model spending has daily and monthly ceilings. A turn's worst-case cost is held before any model call. If a limit check can't run, the chat stays closed.
- **A privacy screen reads the question before anything else does,** and reads the answer again as it streams, holding back the last few words until they have been checked. The screen compares salted hashes stored in the database, so this public code holds none of the terms it screens for.
- **Retrieval is done by code.** Vector search (pgvector) and Postgres full-text search run side by side, reciprocal rank fusion merges the results, and the top 8 passages go forward. No model writes a database query.
- **One optional public lookup.** A small model may name one company, technology or industry that needs public information. Code runs that single lookup, so the model writing the answer can't start a search.
- **Claude writes from the passages** in one streaming call with no tools. Claims about me have to come from a passage; anything the passages don't cover is reported as not in the record. Links in an answer survive only if they point to this site or the live demo.
- **Least-privilege database roles.** The chat function can read the published passages and call a few fixed functions. The roles that save records can add rows and can't read them back.
- **Each turn is logged** with the passages it cited, so quality can be checked rather than assumed. The [What is saved](https://www.rakimfrancis.com/what-is-saved) page lists what is kept.

The case studies the chatbot reads from (`content/`) and the evaluation cases are kept out of this repository on purpose.

## Layout

- `frontend/`: the React and TypeScript app, built with Vite and Tailwind. `src/projects.json` holds the project pages; `public/` holds static files such as the favicon, the link-preview image, `robots.txt` and `sitemap.xml`.
- `frontend/api/`: the Vercel Python functions, each one self-contained file: `chat.py` (the chatbot, streamed as server-sent events), `contact.py` (the contact form) and `track.py` (visit events). `requirements.txt` pins their dependencies to exact versions.
- `backend/`: a FastAPI app with SQLModel and SQLite, for local development only. `app/seed.py` is where the project page text is written; `dump_projects.py` rebuilds `frontend/src/projects.json` from it.
- `db/`: SQL for the chatbot's schema, roles and functions (`site_schema.sql`) and the contact form's daily limits (`leads_limits.sql`).
- `scripts/`: local maintenance scripts that never run on the deployed site. They set up the database and roles, load the privacy screen, build the retrieval index, load organization context, report on and prune the logs, and serve the application programming interface (API) locally (`dev_api.py`). Secrets come from an env file kept outside the repository.
- `tests/`: the pytest suite, 1,079 tests. It runs on fakes: no test calls a model, a web service or a database.
- `eval/`: the chatbot evaluation runner. The cases and results stay local; [eval/README.md](eval/README.md) describes how it grades.

## Running it locally

The front end needs Node 20.19+ or 22.12+, the versions Vite 8 supports:

```sh
cd frontend
npm install
npm run dev        # http://localhost:5173
```

In development Vite forwards `/api` to `127.0.0.1:8787`, where `scripts/dev_api.py` serves the same routes the deployed functions do:

```sh
python scripts/dev_api.py --env-file PATH_TO_ENV_FILE
```

To change a project page, edit `backend/app/seed.py`, then regenerate the baked copy:

```sh
cd backend
uv run python dump_projects.py
```

## Tests and checks

With Python 3.12 and the packages in `frontend/requirements.txt` plus `pytest`, from the repository root:

```sh
python -m pytest -q
```

A few tests run the front end's link checks through Node and are skipped when Node isn't installed.

The offline index check splits the case studies into passages and runs every passage through the privacy screen, with no database and no embedding calls. It needs the local `content/` folder and a terms file (by default `blocklist.txt` in the private folder set by `SITE_SECRETS_DIR`; `--terms PATH` points elsewhere):

```sh
python scripts/build_index.py --offline
```

The front end has its own build and lint:

```sh
cd frontend
npm run build
npm run lint
```
