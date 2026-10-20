# Burrows Field matchday page

A one-page website showing Leckhampton Rovers Youth home games at Burrows Field: kick-off times and pitch allocations, by weekend, by pitch, or for one team.

The fixtures come from FA Full-Time and refresh automatically every **Monday and Friday evening**.

## How it works

| Part | What it does |
| --- | --- |
| `index.html` | The webpage. Loads `fixtures.json` and shows it. |
| `fixtures.json` | The fixture list. Rewritten by the update script, never edited by hand. |
| `scripts/update.py` | Reads Full-Time and writes `fixtures.json`. |
| `.github/workflows/update-fixtures.yml` | Runs the script on Mondays and Fridays and saves the result. |

The script reads four sources and keeps only games whose venue is Burrows Field:

1. **Club feed**: the club's Full-Time code snippet (code `103522507`). This covers all Leckhampton Rovers Youth games in the Cheltenham Youth Football League except U8s.
2. **U8 round robins**: the Cheltenham Youth Football League fixtures list, U8 age group. This adds U8 games between visiting clubs at Burrows Field and the goal set-up notes.
3. **Girls League**: the Gloucester County Girls League fixtures list.
4. **County Cups**: the Gloucestershire FA County Cups fixtures list.

If one source fails on a run, the page keeps that source's games from the previous run and shows a note saying which part couldn't be refreshed. If every source fails, nothing is changed and GitHub emails the repository owner.

## Pitches

The pitch is read from the venue text on Full-Time, for example `BURROWS FIELD #4` or `BURROWS FIELD 9v9 - Pitch #4`. Girls League 5v5 Pitch 1 is treated as a separate pitch from Pitch 1. A "Pitch clash on Full-Time" warning appears when two games are listed on the same pitch at the same kick-off.

## Common jobs

- **Refresh now** (for example after a late postponement): go to the **Actions** tab → **Update fixtures** → **Run workflow**.
- **New season**: nothing to do. The script picks the current season on Full-Time automatically.
- **Club snippet replaced**: if a new code snippet is generated in Full-Time admin, change `CLUB_SNIPPET_CODE` at the top of `scripts/update.py`.
- **A run failed**: open the run in the **Actions** tab. The log names the source and the reason. A `Cloudflare check` or `HTTP 403` means Full-Time refused the request from GitHub's servers.

## Hosting

The page is served by GitHub Pages from the `main` branch. In the repository's **Settings → Pages**, set the source to *Deploy from a branch*, branch `main`, folder `/ (root)`. To use a club web address, add it under **Custom domain** there and point a CNAME record at `jasarge84-sys.github.io`.
