# sources.md

## Source hierarchy

### 1. Official FIFA sources
Primary use:
- official match schedule
- results
- standings
- regulations
- squads
- disciplinary information
- match reports

Current preferred official sources:
- FIFA tournament site pages for World Cup 2026
- FIFA regulations PDF: `https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf`

### 2. Team-strength inputs
Primary public baseline:
- World Football Elo Ratings: `https://eloratings.net/`

Secondary or validation options:
- official FIFA rankings
- a self-built Elo from public historical international match results

### 3. Roster and injury inputs
Allowed sources:
- FIFA official tournament pages
- national federation announcements
- club announcements
- reputable news reporting with clear sourcing

Not allowed:
- rumor aggregators
- anonymous social accounts
- paid injury feeds behind access controls

### 4. Public consensus comparison
Use only for benchmarking divergence:
- public sportsbook-implied outright prices where visible without login
- public supercomputer forecasts where fully public
- public exchange or prediction-market pages if accessible without login and permitted

### 5. Advanced stats
Use only if publicly accessible and permitted for automated access.
If uncertain, do not automate.

## Snapshot logging standard
For every source snapshot, save:
- date
- Eastern Time retrieval time
- source name
- URL
- what fields were used
- any access caveat

## Initial retrieval log
- 2026-06-23 09:46:03 EDT — FIFA regulations PDF located via public web search
- 2026-06-23 09:46:03 EDT — FIFA tournament explainer page on groups and tie-breakers located via public web search
- 2026-06-23 09:46:03 EDT — World Football Elo Ratings located via public web search
