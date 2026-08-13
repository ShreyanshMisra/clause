# Deploy

## Backend (Render, free)
1. Push this repo to GitHub.
2. In Render: New > Blueprint, point at the repo (uses `backend/render.yaml`).
3. Set env vars: `GEMINI_API_KEY` (required), `ALLOWED_ORIGINS` = your Vercel URL (e.g. `https://clause.vercel.app`).
4. Deploy. Note the service URL (e.g. `https://clause-backend.onrender.com`).

## Frontend (Vercel, free)
1. In Vercel: New Project > import this repo, set Root Directory to `frontend/`.
2. Set env var `NEXT_PUBLIC_API_URL` = your Render URL.
3. Deploy.

## After deploy
- Update Render `ALLOWED_ORIGINS` to the final Vercel domain.
- Smoke test: upload `old_reference/.../public/sample-lease.pdf` → results → download demand letter.
- Note: Render free tier cold-starts (~50s) after idle; the upload screen pings `/health` to warm it.
