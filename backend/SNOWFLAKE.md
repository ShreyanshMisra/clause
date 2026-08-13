# Snowflake Cortex mode (for the demo)

Clause has a **swappable retrieval backend**:

| Mode | `VECTOR_BACKEND` | Embeddings | Vector search | Analysis + letter |
|------|------------------|-----------|---------------|-------------------|
| **Free / public** | `local` | Gemini (`gemini-embedding-001`) | in-memory cosine | Gemini |
| **Cortex demo** | `snowflake` | **Snowflake Cortex `EMBED_TEXT_768`** | **`VECTOR_COSINE_SIMILARITY`** | Gemini |

In Cortex mode, Snowflake Cortex powers the whole embeddings + semantic-search (RAG) layer in-database; Gemini only does the clause reasoning and demand-letter drafting. So the demo needs **both** a Snowflake connection **and** `GEMINI_API_KEY`.

---

## Setup on the Snowflake site (you've already started the free trial)

### 1. Find your account identifier
In **Snowsight** (app.snowflake.com), bottom-left → your account → **Account details** (or **View account details**). Copy the **Account Identifier**, e.g. `ABCDEFG-XY12345`. That's your `SNOWFLAKE_ACCOUNT`.

### 2. Create the warehouse, database, schema, and table
Open a new **Worksheet** (use role **ACCOUNTADMIN**), paste the contents of `backend/snowflake_setup.sql`, and **Run All**. It creates:
- warehouse `CLAUSE_WH` (X-Small, auto-suspend 60s — keeps trial credits low),
- database `CLAUSE_DB`, schema `PUBLIC`,
- table `STATUTES(... embedding VECTOR(FLOAT, 768))`.

### 3. Confirm Cortex is available in your region
In the worksheet, run:
```sql
SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m-v1.5', 'hello world');
```
- **Returns a 768-number vector** → you're good.
- **Errors** ("unknown function" / "model not available") → your trial region doesn't have that model. Either recreate the trial in an AWS US region (e.g. `us-east-1`, `us-west-2`), or set `CORTEX_EMBED_MODEL` to a model your region lists under Snowsight → **AI & ML → Cortex**. (Whatever model you pick must be a 768-dim `EMBED_TEXT_768` model to match the table.)

Cortex functions are granted to everyone by default via the `SNOWFLAKE.CORTEX_USER` role; if you locked down roles, grant it:
```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <your_role>;
```

### 4. Gather credentials
- `SNOWFLAKE_ACCOUNT` = the identifier from step 1
- `SNOWFLAKE_USER` / `SNOWFLAKE_PASSWORD` = your Snowsight login
- `SNOWFLAKE_WAREHOUSE=CLAUSE_WH`, `SNOWFLAKE_DATABASE=CLAUSE_DB`, `SNOWFLAKE_SCHEMA=PUBLIC`

---

## Run Clause in Cortex mode

### 1. Seed the statutes (one time)
This embeds the 8 MA statutes with Cortex and inserts them into `STATUTES`:
```bash
cd backend && source .venv/bin/activate
VECTOR_BACKEND=snowflake \
SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=... \
SNOWFLAKE_WAREHOUSE=CLAUSE_WH SNOWFLAKE_DATABASE=CLAUSE_DB SNOWFLAKE_SCHEMA=PUBLIC \
python -m app.seed_statutes
# -> Seeded 8 statutes into snowflake store.
```
Verify in a worksheet: `SELECT COUNT(*) FROM CLAUSE_DB.PUBLIC.STATUTES;` → 8.

### 2. Point the app at Snowflake
Set these in `backend/.env` (for local) or on Render (for the deployed demo), keeping `GEMINI_API_KEY`:
```
VECTOR_BACKEND=snowflake
GEMINI_API_KEY=...
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=CLAUSE_WH
SNOWFLAKE_DATABASE=CLAUSE_DB
SNOWFLAKE_SCHEMA=PUBLIC
```
Restart the backend. On startup it will **not** seed the local store; every analysis embeds each lease page with Cortex and retrieves via `VECTOR_COSINE_SIMILARITY`.

### 3. Switch back to free (public demo)
Set `VECTOR_BACKEND=local` (and you can drop the `SNOWFLAKE_*` vars). No re-seed needed — the local store re-seeds itself on startup with Gemini embeddings.

---

## Cost control (trial credits)
- `CLAUSE_WH` is X-Small with `AUTO_SUSPEND=60`, so it sleeps 60s after the last query.
- Each analysis is ~1 Cortex embed per lease page (≤20). Suspend the warehouse when you're done: `ALTER WAREHOUSE CLAUSE_WH SUSPEND;`
- Flip to `VECTOR_BACKEND=local` whenever you're not filming to stop all Snowflake usage.
