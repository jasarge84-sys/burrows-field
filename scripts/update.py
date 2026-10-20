"""Build fixtures.json for the Burrows Field page from FA Full-Time.

Sources (each one succeeds or fails on its own; a failed source keeps its last good data):
  club   - the club's Full-Time code snippet (all Leckhampton Rovers Youth games in the
           Cheltenham Youth Football League). U8 games are skipped here and taken from "u8".
  u8     - Cheltenham Youth Football League fixtures list, U8 age group only. Picks up U8
           round-robin games between visiting clubs at Burrows Field, plus match notes.
  girls  - Gloucester County Girls League fixtures list.
  women  - Gloucestershire County Women's Football League fixtures list (Leckhampton Rovers Women).
  cups   - Gloucestershire FA County Cups fixtures list.
Only games whose venue mentions Burrows Field are kept.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE = "https://fulltime.thefa.com"
CLUB_SNIPPET_CODE = "103522507"
CYFL_LEAGUE = "4333696"
GIRLS_LEAGUE = "1073825"
WOMENS_LEAGUE = "879242925"
CUPS_LEAGUE = "912256431"
VENUE_MATCH = re.compile(r"BURROWS", re.I)
UK = ZoneInfo("Europe/London")
OUT = Path(__file__).resolve().parent.parent / "fixtures.json"
STATUS_WORDS = re.compile(r"postpon|cancel|abandon|void|walkover|withdrawn|tbc|re-?arranged", re.I)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Leckhampton Rovers Youth Burrows Field fixtures page; twice weekly)",
    "Accept-Language": "en-GB,en;q=0.9",
})


class SourceError(Exception):
    pass


def get(url: str) -> str:
    """Fetch a Full-Time URL politely, with a couple of retries."""
    last = None
    for attempt in range(3):
        try:
            r = session.get(url, timeout=40)
            body = r.text
            if r.status_code == 200 and "Just a moment" not in body[:2000] and "cf-chl" not in body[:5000]:
                time.sleep(1.5)  # be gentle with the FA's servers
                return body
            last = f"HTTP {r.status_code}" + (" (Cloudflare check)" if "cf-" in body[:5000] else "")
        except requests.RequestException as e:
            last = str(e)
        time.sleep(5 * (attempt + 1))
    raise SourceError(f"Could not fetch {url.split('?')[0]}: {last}")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def parse_venue(venue: str) -> tuple[str, str]:
    """'BURROWS FIELD #4' -> ('4', ''); 'BURROWS FIELD 9v9 - Pitch #4' -> ('4', '9v9')."""
    m = re.search(r"#\s*([0-9]+[A-Z]?)", venue, re.I)
    pitch = m.group(1).upper() if m else "?"
    f = re.search(r"(\d+)\s*v\s*(\d+)", venue, re.I)
    return pitch, (f"{f.group(1)}v{f.group(2)}" if f else "")


def is_u8(*names: str) -> bool:
    return any(re.search(r"\bU8\b", n) for n in names)


def fixture(**kw) -> dict:
    pitch, fmt = parse_venue(kw.pop("venue"))
    return {"pitch": pitch, "format": fmt, "comp": "", "type": "", "notes": "", "id": "", **kw}


# ---------- Source: club code snippet ----------

def fetch_club_snippet() -> list[dict]:
    stamp = datetime.now(UK).strftime("%Y%m%d%H%M")
    text = get(f"{BASE}/js/cs1.html?cs={CLUB_SNIPPET_CODE}&random={stamp}")
    m = re.match(r"\s*document\.getElementById\('[^']*'\)\.innerHTML\s*=\s*'(.*)';\s*$", text, re.S)
    if not m:
        raise SourceError("Club feed came back in an unexpected format")
    soup = BeautifulSoup(m.group(1).replace("\\'", "'"), "html.parser")
    out, when, last = [], None, None
    seen_rows = 0
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 1:
            txt = clean(tds[0].get_text())
            try:
                when = datetime.strptime(txt, "%a %d %b %Y %H:%M")
                continue
            except ValueError:
                pass
            if last is not None and txt:  # status line under a game, e.g. "Postponed"
                last["notes"] = txt
            continue
        link = tr.find("a", href=re.compile(r"displayFixture"))
        if not link or len(tds) < 5 or when is None:
            continue
        seen_rows += 1
        cells = [clean(td.get_text()) for td in tds]
        typ, home, away, venue = cells[0], cells[1], cells[3], cells[4]
        last = None
        if not VENUE_MATCH.search(venue) or is_u8(home, away):
            continue
        last = fixture(date=when.strftime("%Y-%m-%d"), time=when.strftime("%H:%M"), home=home, away=away,
                       venue=venue, type=typ, league="C", source="club",
                       id=link["href"].split("id=")[-1])
        out.append(last)
    if seen_rows == 0:
        raise SourceError("Club feed had no fixtures in it")
    return out


# ---------- Source: league fixtures pages ----------

def option_value(soup: BeautifulSoup, select_id: str, label: str | None = None) -> str | None:
    sel = soup.find("select", id=select_id)
    if not sel:
        return None
    for o in sel.find_all("option"):
        if label is None and o.has_attr("selected"):
            return o["value"]
        if label is not None and clean(o.get_text()) == label:
            return o["value"]
    return None


def fetch_league(league: str, tag: str, source: str, age_group: str | None = None) -> list[dict]:
    first = BeautifulSoup(get(f"{BASE}/fixtures.html?league={league}&selectedDateCode=all"), "html.parser")
    season = option_value(first, "form1_selectedSeason")
    if not season:
        raise SourceError(f"Could not find the current season for league {league}")
    age = "0"
    if age_group:
        age = option_value(first, "form1_selectedFixtureGroupAgeGroup", age_group)
        if not age:
            raise SourceError(f"No {age_group} age group in league {league} this season")
    q = (f"?league={league}&selectedSeason={season}&selectedFixtureGroupAgeGroup={age}"
         "&previousSelectedFixtureGroupAgeGroup=&selectedFixtureGroupKey=&previousSelectedFixtureGroupKey="
         "&selectedDateCode=all&selectedRelatedFixtureOption=3&selectedClub=&previousSelectedClub="
         "&selectedTeam=&selectedFixtureDateStatus=&selectedFixtureStatus=")
    out, total = [], 0
    for page in range(1, 41):
        soup = BeautifulSoup(get(f"{BASE}/fixtures/{page}/200.html{q}"), "html.parser")
        if page == 1 and not soup.select_one(".fixtures-table"):
            raise SourceError(f"League {league} fixtures page has no fixtures table")
        rows = soup.select(".fixtures-table tbody tr")
        total += len(rows)
        for tr in rows:
            home_td, away_td = tr.select_one("td.home-team"), tr.select_one("td.road-team")
            if not home_td or not away_td:
                continue
            tds = tr.find_all("td", recursive=False)
            i = tds.index(away_td)
            venue = clean(tds[i + 1].get_text()) if len(tds) > i + 1 else ""
            if not VENUE_MATCH.search(venue):
                continue
            comp = clean(tds[i + 2].get_text()) if len(tds) > i + 2 else ""
            notes_td = tr.select_one("td.status-notes")
            notes = re.sub(r"^Match Notes:\s*", "", clean(notes_td.get_text()) if notes_td else "", flags=re.I)
            spans = [clean(s.get_text()) for s in tds[1].find_all("span")]
            dt = " ".join(spans) if spans else clean(tds[1].get_text())
            m = re.search(r"(\d{2})/(\d{2})/(\d{2})(?:\s+(\d{1,2}:\d{2}))?", dt)
            if not m:
                continue
            link = tr.find("a", href=re.compile(r"display(County)?Fixture"))
            out.append(fixture(date=f"20{m.group(3)}-{m.group(2)}-{m.group(1)}", time=m.group(4) or "",
                               home=clean(home_td.get_text()), away=clean(away_td.get_text()), venue=venue,
                               comp=comp, type=clean(tds[0].get_text()), notes=notes, league=tag, source=source,
                               id=(link["href"].split("id=")[-1].split("&")[0] if link else "")))
        if len(rows) < 200:
            break
    return out


SOURCES = {
    "club":  ("Leckhampton games (club feed)", fetch_club_snippet),
    "u8":    ("U8 round robins", lambda: fetch_league(CYFL_LEAGUE, "C", "u8", age_group="U8")),
    "girls": ("Girls League", lambda: fetch_league(GIRLS_LEAGUE, "G", "girls")),
    "women": ("Women's League", lambda: fetch_league(WOMENS_LEAGUE, "W", "women")),
    "cups":  ("County Cups", lambda: fetch_league(CUPS_LEAGUE, "X", "cups")),
}


def main() -> int:
    now = datetime.now(UK).replace(microsecond=0)
    prev = {"sources": {}, "fixtures": []}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
        except json.JSONDecodeError:
            pass

    fixtures, status, failures = [], {}, 0
    for key, (label, fn) in SOURCES.items():
        try:
            rows = fn()
            fixtures += rows
            status[key] = {"label": label, "ok": True, "updated": now.isoformat(), "count": len(rows), "error": None}
            print(f"{key}: {len(rows)} games at Burrows Field")
        except Exception as e:  # keep the last good data for this source
            failures += 1
            old = [f for f in prev.get("fixtures", []) if f.get("source") == key]
            fixtures += old
            was = prev.get("sources", {}).get(key, {})
            status[key] = {"label": label, "ok": False, "updated": was.get("updated"), "count": len(old), "error": str(e)}
            print(f"::warning::{label} failed, keeping {len(old)} games from last time: {e}")

    # Drop games more than a week old, de-duplicate, sort
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    seen, rows = set(), []
    for f in sorted(fixtures, key=lambda f: (f["date"], f["time"], f["pitch"], f["home"])):
        k = (f["date"], f["time"], f["home"], f["away"])
        if f["date"] >= cutoff and k not in seen:
            seen.add(k)
            rows.append(f)

    data = {"generated": now.isoformat(), "sources": status, "fixtures": rows}
    if failures == len(SOURCES):
        print("::error::Every source failed; fixtures.json left unchanged.")
        return 1
    # Always rewrite, so the page's "checked" time moves forward even when nothing changed
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} games to {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
