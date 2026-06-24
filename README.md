# 2026 World Cup Forecast

Independent, public-data 2026 FIFA World Cup forecast.

## Current setup
- Public FIFA match feed ingestion
- Public World Football Elo baseline
- Saved snapshots under `state/`
- Static shareable site built to `site/index.html`
- GitHub Pages workflow in `.github/workflows/github-pages.yml`

## Local rebuild
```bash
python scripts/run_forecast.py
python app/build_public_site.py
```

## Publish on GitHub Pages
1. Create a GitHub repo and push this project.
2. In GitHub, go to **Settings → Pages**.
3. Set **Source** to **GitHub Actions**.
4. Push to `main` or `master`.
5. The workflow will build `site/` and publish it automatically.

## Important caveat
The site is already shareable, but title odds are still first-pass heuristic outputs until the full tournament simulator is finished.
