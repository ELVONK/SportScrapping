import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as dateparser

TIMEZONE_DELTA = timedelta(hours=3)  # EAT (UTC+3)

def get_odibets_matches():
    url = "https://odibets.com/oditoday"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    matches = []
    for evt in soup.select(".match-event"):
        title = evt.select_one(".event-title")
        time_el = evt.select_one(".event-time")
        if not title or not time_el:
            continue
        team = title.text.strip()
        t = time_el.text.strip()
        dt = dateparser.parse(t, default=datetime.now())
        dt = dt.replace(tzinfo=None) + TIMEZONE_DELTA
        matches.append({"team": team, "time": dt})
    return matches

def get_flash_matches():
    url = "https://www.flashscore.co.ke/football/kenya/kpl/fixtures/"
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    matches = []
    for row in soup.select(".sportNameFootball ~ .event__match"):
        home = row.select_one(".event__participant--home")
        away = row.select_one(".event__participant--away")
        time_el = row.select_one(".event__time")
        if not (home and away and time_el):
            continue
        team = f"{home.text.strip()} vs {away.text.strip()}"
        t = time_el.text.strip()
        dt = dateparser.parse(t, default=datetime.now())
        dt = dt.replace(tzinfo=None) + TIMEZONE_DELTA
        matches.append({"team": team, "time": dt})
    return matches

def compare(odi, flash):
    now = datetime.now() + TIMEZONE_DELTA
    flash_map = {m['team'].lower(): m['time'] for m in flash}
    late, played = [], []

    for m in odi:
        key = m['team'].lower()
        if key in flash_map:
            if flash_map[key] < now:
                late.append((m, flash_map[key]))
        else:
            # Assume it's yesterday if older than today-1
            if m['time'].date() < (now.date()):
                played.append(m)
    return late, played

def main():
    odi = get_odibets_matches()
    flash = get_flash_matches()
    late, played = compare(odi, flash)

    print("=== LATE MATCHES (odibets lists but flashscore already started/ended):")
    for o, f in late:
        print(f"{o['team']} — Odibets: {o['time']} | Flashscore: {f}")

    print("\n=== ODBIETS MATCHES FROM YESTERDAY (not in today's Flashscore):")
    for o in played:
        print(f"{o['team']} — Scheduled: {o['time']}")

if __name__ == "__main__":
    main()
