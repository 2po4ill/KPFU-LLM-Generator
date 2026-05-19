# RPD UI Smoke Guide

## UI
Static single-page app (`index.html` + `styles.css` + `app.js`):
- 3-step flow: API → upload RPD → sources & generate
- Settings collapsed by default
- Source list as cards (not a wide table)
- API log in collapsible panel

## Purpose
Minimal static UI for:
- upload RPD file
- inspect discovered sources
- selectively resolve direct PDF sources
- trigger single-theme generation

## GitHub Pages

Static UI is deployed from `web/rpd-ui/` via GitHub Actions (`.github/workflows/deploy-rpd-ui-pages.yml`).

**URL (after enable):** `https://2po4ill.github.io/KPFU-LLM-Generator/`

### One-time setup in GitHub repo

1. **Settings → Pages → Build and deployment → Source:** `GitHub Actions`
2. Push to `main` (or run workflow manually: Actions → Deploy RPD UI)

### Using the hosted UI

- Backend is **not** on Pages — only the static frontend.
- In **Настройки API** set **Адрес сервера**, e.g. `http://127.0.0.1:8000/api/v1` (local) or your public API URL.
- Backend CORS is open (`allow_origins=["*"]` in `app/main.py`).
- If API key is configured on the server, enter it in the UI.

### Run Locally
1. Start backend FastAPI (`/api/v1` must be available).
2. Open static UI:
   - simplest: open `web/rpd-ui/index.html` in browser, or
   - serve folder (`python -m http.server`) and open `http://127.0.0.1:8000/web/rpd-ui/`.
3. In UI, set:
   - API base, e.g. `http://127.0.0.1:8000/api/v1`
   - `X-API-Key` if backend uses it.

## Smoke Scenario
1. Upload one RPD file via **"Загрузить и разобрать РПД"**.
2. Verify:
   - `rpd_id` displayed.
   - themes list populated.
   - discovered sources table populated.
3. Press **"Выбрать все direct_pdf"** (or select manually), then **resolve**.
4. Press **refresh** and verify statuses/counters:
   - expected statuses: `ok`, `duplicate_ok`, `failed`, `skipped`.
   - populated `book_id` for successful entries.
5. Select theme, set generation flags (PPTX / lab / self-check), press **"Сгенерировать пакет"**.
6. In **Проверка экспертом**: edit markdown, preview, press **"Утвердить для экспорта"**.
7. Export SCORM, PDF bundle, or PPTX.
8. Verify log includes generation metadata:
   - `generation_time_seconds`
   - `confidence_score`
   - `cached`
   - `step_times`

## Negative Cases
- Invalid/broken PDF URL in sources -> status `failed`, non-empty `error`.
- Non-PDF source page (`http_page`) -> status `skipped`, reason `ebs_or_portal_link_not_automated`.
- Unknown/invalid `rpd_id` in session/resolve -> backend 404.
- API key mismatch -> backend 401.
- Rate limit exceeded -> backend 429.

- Rate limit exceeded -> backend 429.

## GitHub Pages Notes (legacy)

See section **GitHub Pages** above.
