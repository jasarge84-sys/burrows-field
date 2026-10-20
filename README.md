# Burrows Field matchday page

A one-page website showing Leckhampton Rovers Youth home games at Burrows Field: kick-off times and pitch allocations, by weekend, by pitch, or for one team.

Fixtures come from FA Full-Time. Leckhampton's Cheltenham Youth League games load **live** in each visitor's browser from the club's Full-Time code snippet, so they're always current. Everything else comes from `fixtures.json`, a saved snapshot.

## How it works

| Part | What it does |
| --- | --- |
| `index.html` | The webpage. Loads the live code snippet(s) listed in `SNIPPETS` near the bottom, plus `fixtures.json` for everything else. |
| `fixtures.json` | The fixture list. Rewritten by the update script, never edited by hand. |
| `scripts/update.py` | Reads Full-Time and writes `fixtures.json`. |
| `.github/workflows/update-fixtures.yml` | Runs the script and saves the result (manual only: see below). |

### Live snippets

Any Full-Time code snippet can be added to the `SNIPPETS` list in `index.html` (its code is the `lrcode` number in the snippet). A snippet replaces that part of the snapshot. If a snippet fails to load, the page falls back to the snapshot and says so. Getting snippets for the **Girls League** (club fixtures) and the **Cheltenham league U8 Development** division would make the whole page live.

### Snapshot (`fixtures.json`)

The script reads four sources and keeps only games whose venue is Burrows Field:

1. **Club feed**: the club's Full-Time code snippet (code `103522507`). This covers all Leckhampton Rovers Youth games in the Cheltenham Youth Football League except U8s.
2. **U8 round robins**: the Cheltenham Youth Football League fixtures list, U8 age group. This adds U8 games between visiting clubs at Burrows Field and the goal set-up notes.
3. **Girls League**: the Gloucester County Girls League fixtures list.
4. **County Cups**: the Gloucestershire FA County Cups fixtures list.

If one source fails on a run, the page keeps that source's games from the previous run and shows a note saying which part couldn't be refreshed. If every source fails, nothing is changed and GitHub emails the repository owner.

## Pitches

The pitch is read from the venue text on Full-Time, for example `BURROWS FIELD #4` or `BURROWS FIELD 9v9 - Pitch #4`. Girls League 5v5 Pitch 1 is treated as a separate pitch from Pitch 1. A "Pitch clash on Full-Time" warning appears when two games are listed on the same pitch at the same kick-off.

## Common jobs

- **Refresh the snapshot**: run `scripts/update.py` from a home computer (`pip install requests beautifulsoup4`, then `python scripts/update.py`) and commit `fixtures.json`. GitHub's servers are blocked by Full-Time, so the **Run workflow** button in the Actions tab currently fails safely without changing anything.
- **New season**: nothing to do. The script picks the current season on Full-Time automatically.
- **Club snippet replaced**: if a new code snippet is generated in Full-Time admin, change `CLUB_SNIPPET_CODE` at the top of `scripts/update.py`.
- **A run failed**: open the run in the **Actions** tab. The log names the source and the reason. A `Cloudflare check` or `HTTP 403` means Full-Time refused the request from GitHub's servers.

## Hosting

The page is served by GitHub Pages from the `main` branch. In the repository's **Settings → Pages**, set the source to *Deploy from a branch*, branch `main`, folder `/ (root)`. To use a club web address, add it under **Custom domain** there and point a CNAME record at `jasarge84-sys.github.io`.
