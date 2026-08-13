# Switching to Snowflake (optional)

By default the app uses an in-memory vector store (`VECTOR_BACKEND=local`, free). To use Snowflake trial credits:

## 1. Create schema
Run `backend/snowflake_setup.sql` in a Snowflake worksheet (creates an XS auto-suspend warehouse, DB, schema, and the `STATUTES` table with a `VECTOR(FLOAT, 768)` column matching Gemini `text-embedding-004`).

## 2. Seed statutes
Locally, with env vars set:
```bash
cd backend && source .venv/bin/activate
export VECTOR_BACKEND=snowflake
export GEMINI_API_KEY=...        # embeds the corpus
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_USER=...
export SNOWFLAKE_PASSWORD=...
export SNOWFLAKE_WAREHOUSE=CLAUSE_WH
export SNOWFLAKE_DATABASE=CLAUSE_DB
export SNOWFLAKE_SCHEMA=PUBLIC
python -m app.seed_statutes   # prints: Seeded 8 statutes into snowflake store.
```

## 3. Point the backend at Snowflake
On Render, set `VECTOR_BACKEND=snowflake` and the `SNOWFLAKE_*` env vars, then redeploy. With `VECTOR_BACKEND=snowflake` the startup no longer seeds the local store; retrieval reads from Snowflake via `VECTOR_COSINE_SIMILARITY`.

## Cost control
XS warehouse + `AUTO_SUSPEND=60` keeps trial-credit burn minimal (suspends 60s after idle). To fall back to free, set `VECTOR_BACKEND=local` and redeploy.
