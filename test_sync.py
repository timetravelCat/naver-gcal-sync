"""convert() 확인용. 실행: python test_sync.py"""
from icalendar import Calendar

from sync import convert

ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:a
SUMMARY:미용실
DTSTART;TZID=Asia/Seoul:20261010T140000
DTEND;TZID=Asia/Seoul:20261010T150000
END:VEVENT
BEGIN:VEVENT
UID:b
SUMMARY:여행
DTSTART;VALUE=DATE:20261012
END:VEVENT
BEGIN:VEVENT
UID:c
STATUS:CANCELLED
DTSTART;VALUE=DATE:20261013
END:VEVENT
END:VCALENDAR
"""

timed, allday, cancelled = Calendar.from_ical(ICS).walk("VEVENT")

ev = convert(timed, "cal")
assert ev["start"]["dateTime"] == "2026-10-10T14:00:00+09:00", ev["start"]
assert ev["end"]["dateTime"] == "2026-10-10T15:00:00+09:00", ev["end"]
assert ev["extendedProperties"]["private"]["naverSync"] == "1"
assert ev["id"] == convert(timed, "cal")["id"] != convert(timed, "other")["id"]

ev = convert(allday, "cal")
assert ev["start"] == {"date": "2026-10-12"} and ev["end"] == {"date": "2026-10-13"}

assert convert(cancelled, "cal") is None
print("ok")
