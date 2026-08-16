# Clause

Clause is an AI-powered contract management platform that detects illegal clauses in legal agreements. After you upload a legal document, our system detects violations, analyzes potential risks with statute citations, and can generate a ready-to-send demand letter. PII is stripped from the document before any text reaches an LLM.

This repository is a lightweight demo version of the original Clause codebase, built with @SonnyZhan, @sh1v-ansh, and @JineshwarNariani. The original project was developed for HackUMass.

### Tech Stack
- **Backend** — FastAPI, SQLite, Gemini API, Snowflake Cortex, PyMuPDF, Presidio, WeasyPrint
- **Frontend** — React, Next.js, Tailwind, `react-pdf-highlighter`.
