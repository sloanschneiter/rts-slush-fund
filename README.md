# May Budget Diff — Slush Fund Dashboard

Shared, editable web dashboard tracking line-by-line May FC budget changes
(true original vs current paid marketing budget) across Havenly, Burrow,
Citizenry, and Interior Define.

- Positive amount = cut/savings
- Negative amount = added spend
- Net per brand shown at the top of each section
- All edits shared in real time via Turso

## Stack

- Streamlit Cloud (Python 3.12)
- Turso (libSQL) — shared SQLite via HTTP API
- No password — fully public

## Local dev

```sh
python -m venv .venv
.venv\Scripts\activate          # PowerShell
pip install -r requirements.txt

# Copy the secrets template and fill in:
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# (edit .streamlit/secrets.toml)

streamlit run app.py
```

## Deploy

1. Create a Turso DB at https://turso.tech and copy the URL + auth token.
2. Push this repo to GitHub.
3. On Streamlit Cloud, deploy the repo and paste the two secrets
   (`turso_database_url`, `turso_auth_token`) into App settings → Secrets.

The schema bootstraps and seeds the May budget diff data on first run.
