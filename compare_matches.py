import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv

TELEGRAM_TOKEN = "8018191864:AAER7Niw0Ao3e25p-3DDnLDx6AanLjM2LRU"
CHAT_ID = "1196282706"

TIMEZONE_OFFSET = timedelta(hours=3)

def send_telegram_message(message):
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": message}
try:
requests.post(url, data=payload)
except Exception as e:
print(f"Telegram Error: {e}")

def get_odibets_matches():
url = "https://odibets.com/oditoday"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")
matches = []
for match in soup.select(".match-event"):
    try:
        team = match.select_one(".event-title").text.strip()
        time_str = match.select_one(".event-time").text.strip()
        match_time = datetime.strptime(time_str, "%H:%M").replace(
            year=datetime.now().year, 
            month=datetime.now().month, 
            day=datetime.now().day
        ) + TIMEZONE_OFFSET
        matches.append({"team": team, "time": match_time})
    except:
        continue
return matches
def get_flashscore_matches(date):
formatted_date = date.strftime("%Y-%m-%d")
url = f"https://www.flashscore.com/?d={formatted_date}"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(response.text, "html.parser")
matches = []
for match in soup.select(".event__match"):
    try:
        home = match.select_one(".event__participant--home").text.strip()
        away = match.select_one(".event__participant--away").text.strip()
        team = f"{home} vs {away}"
        time_str = match.select_one(".event__time").text.strip()
        match_time = datetime.strptime(time_str, "%H:%M").replace(
            year=date.year, month=date.month, day=date.day
        ) + TIMEZONE_OFFSET
        matches.append({"team": team, "time": match_time})
    except:
        continue
return matches
def compare_matches(odi_matches, flash_today, flash_yesterday):
now = datetime.now() + TIMEZONE_OFFSET
late_matches = []
played_yesterday = []
flash_today_dict = {m['team'].lower(): m['time'] for m in flash_today}
flash_yesterday_teams = {m['team'].lower() for m in flash_yesterday}

for match in odi_matches:
    team = match['team'].lower()
    if team in flash_today_dict and flash_today_dict[team] < now:
        late_matches.append(match)
    elif team in flash_yesterday_teams:
        played_yesterday.append(match)

return late_matches, played_yesterday
def export_to_csv(late, yesterday):
with open("output.csv", "w", newline="", encoding="utf-8") as file:
writer = csv.writer(file)
writer.writerow(["Category", "Team", "Scheduled Time"])
for m in late:
writer.writerow(["Late Today", m["team"], m["time"]])
for m in yesterday:
writer.writerow(["Played Yesterday", m["team"], m["time"]])

def main():
print("Running match checker...")
odi = get_odibets_matches()
today = datetime.now()
yesterday = today - timedelta(days=1)
flash_today = get_flashscore_matches(today)
flash_yesterday = get_flashscore_matches(yesterday)
late, maybe_yesterday = compare_matches(odi, flash_today, flash_yesterday)
export_to_csv(late, maybe_yesterday)

message = f"Match Checker Alert\\nLate Today: {len(late)}\\nPlayed Yesterday: {len(maybe_yesterday)}"
if late or maybe_yesterday:
    send_telegram_message(message)
print(message)
if name == "main":
main()
