# Campus Index

An independent, source-dated college affordability research tool.

## Start locally

Run `python -m http.server 8000` from this directory, then open http://localhost:8000.

## Deploy

Create a public GitHub repository and upload the files, preserving `.github/workflows/refresh-data.yml`. Import into Vercel as a static site (no build command; output directory `.`) and configure `campusindex.me` only after acquiring the domain.

The GitHub Action triggers daily and on updater changes. It fetches **official historical observations** from BLS/FRED, retries temporary network failures, validates series, and commits only when observations actually change. Vercel Git integration should then redeploy on changed commits. Verify this connection on the target account. No data source is replaced with invented points if fetching fails.

**Important:** The College Board 2025–26 sector budget benchmarks are a *manual, source-dated snapshot*. Annual reports must be checked and updated when released; the monthly updater does not silently change annual benchmark figures. Institution-level data from College Scorecard is linked, not yet imported. The site intentionally distinguishes real historical observations, estimates and user-selected assumptions.

## Data sources

- College Board — Trends in College Pricing 2025: https://research.collegeboard.org/trends/college-pricing/highlights
- BLS/FRED tuition, school fees, and childcare CPI (not college-only tuition): https://fred.stlouisfed.org/series/CUSR0000SEEB
- BLS/FRED CPI, all items: https://fred.stlouisfed.org/series/CUSR0000SA0
- BLS/FRED average private hourly earnings: https://fred.stlouisfed.org/series/CES0500000003
- Federal College Scorecard: https://collegescorecard.ed.gov/data/

## Transparency

No investment projections, net price estimates, or historical points are invented. Historical series are live only after successful GitHub Actions update. Dorm and dining splits in the scenario calculator are illustrative.