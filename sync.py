"""네이버 캘린더(CalDAV) -> 구글 캘린더 단방향 동기화.

- 네이버 일정을 읽어 구글 캘린더(GCAL_ID)에 생성/수정/삭제를 반영한다.
- 이 스크립트가 만든 일정만 관리한다(extendedProperties.private.naverSync=1).
- public 저장소의 로그는 누구나 볼 수 있으므로 건수만 출력한다.

환경 변수
  필수: NAVER_ID, NAVER_APP_PW, GCAL_ID, GOOGLE_SA_JSON
  선택: NAVER_CALENDARS  동기화할 네이버 캘린더 이름(쉼표 구분). 비우면 전체.
        PAST_DAYS      과거 범위(일), 기본 30
        FUTURE_DAYS    미래 범위(일), 기본 365
        DEBUG          1이면 오류 전체 출력(로컬 테스트 전용, Actions에서 켜지 말 것)
"""

import hashlib
import json
import os
import sys
import traceback
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import caldav
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

NAVER_URL = "https://caldav.calendar.naver.com/"
KST = ZoneInfo("Asia/Seoul")
TAG_KEY = "naverSync"
HASH_KEY = "h"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        sys.exit(f"missing env: {name}")
    return value


# ---------- 네이버 -> 구글 일정 변환 ----------

def to_gcal_time(v):
    # datetime은 date의 하위 클래스이므로 먼저 검사
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=KST)
        return {"dateTime": v.isoformat(), "timeZone": "Asia/Seoul"}
    if isinstance(v, date):
        return {"date": v.isoformat()}
    raise TypeError(type(v).__name__)


def convert(vevent, cal_key: str):
    if str(vevent.get("STATUS", "")).upper() == "CANCELLED":
        return None
    dtstart = vevent.get("DTSTART")
    if dtstart is None:
        return None

    start = dtstart.dt
    if vevent.get("DTEND") is not None:
        end = vevent["DTEND"].dt
    elif vevent.get("DURATION") is not None:
        end = start + vevent["DURATION"].dt
    elif isinstance(start, datetime):
        end = start + timedelta(hours=1)
    else:
        end = start + timedelta(days=1)  # 종일 일정: 종료일은 다음 날(배타적)

    # 시작과 종료의 형식이 다르면(종일/시간) 시작 형식에 맞춘다
    if isinstance(start, datetime) and not isinstance(end, datetime):
        end = start + timedelta(hours=1)
    if not isinstance(start, datetime) and isinstance(end, datetime):
        end = start + timedelta(days=1)

    uid = str(vevent.get("UID", ""))
    rid = vevent.get("RECURRENCE-ID")
    occurrence = (rid.dt if rid is not None else start).isoformat()
    # 구글 이벤트 ID는 base32hex(a-v, 0-9)만 허용. sha1 hex(0-9a-f)는 그 부분집합.
    event_id = hashlib.sha1(f"{cal_key}|{uid}|{occurrence}".encode()).hexdigest()

    body = {
        "summary": str(vevent.get("SUMMARY", "(제목 없음)")),
        "location": str(vevent.get("LOCATION", "")),
        "description": str(vevent.get("DESCRIPTION", "")),
        "start": to_gcal_time(start),
        "end": to_gcal_time(end),
    }
    digest = hashlib.sha1(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    body["id"] = event_id
    body["extendedProperties"] = {"private": {TAG_KEY: "1", HASH_KEY: digest}}
    return body


def fetch_naver(start: datetime, end: datetime) -> dict:
    client = caldav.DAVClient(
        url=NAVER_URL,
        username=env("NAVER_ID"),
        password=env("NAVER_APP_PW"),
    )
    calendars = client.principal().calendars()

    wanted = {
        n.strip() for n in os.environ.get("NAVER_CALENDARS", "").split(",") if n.strip()
    }
    if wanted:
        selected = [c for c in calendars if (c.get_display_name() or "") in wanted]
    else:
        selected = calendars
    print(f"naver calendars: total={len(calendars)} selected={len(selected)}")

    events: dict = {}
    for cal in selected:
        for obj in cal.search(start=start, end=end, event=True, expand=True):
            for vevent in obj.icalendar_instance.walk("VEVENT"):
                ev = convert(vevent, str(cal.url))
                if ev:
                    events[ev["id"]] = ev
    return events


# ---------- 구글 ----------

def google_service():
    info = json.loads(env("GOOGLE_SA_JSON"))
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_managed(svc, cal_id: str, start: datetime, end: datetime) -> dict:
    items: dict = {}
    page = None
    while True:
        resp = svc.events().list(
            calendarId=cal_id,
            privateExtendedProperty=f"{TAG_KEY}=1",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            showDeleted=False,
            maxResults=2500,
            pageToken=page,
        ).execute()
        for it in resp.get("items", []):
            items[it["id"]] = it
        page = resp.get("nextPageToken")
        if not page:
            return items


def main():
    cal_id = env("GCAL_ID")
    now = datetime.now(KST)
    start = now - timedelta(days=int(os.environ.get("PAST_DAYS", "30")))
    end = now + timedelta(days=int(os.environ.get("FUTURE_DAYS", "365")))

    src = fetch_naver(start, end)
    svc = google_service()
    dst = fetch_managed(svc, cal_id, start, end)
    print(f"naver events={len(src)} google managed={len(dst)}")

    # 안전장치: 네이버 쪽이 비었는데 구글에 많이 남아 있으면 삭제하지 않고 중단
    if not src and len(dst) > 5:
        sys.exit("abort: naver returned 0 events while google has many; skip deletion")

    created = updated = deleted = 0
    events = svc.events()

    for eid, body in src.items():
        cur = dst.get(eid)
        if cur is None:
            try:
                events.insert(calendarId=cal_id, body=body).execute()
                created += 1
            except HttpError as e:
                if e.resp.status != 409:
                    raise
                # 이전에 지워진 같은 ID가 남아 있는 경우: 되살려서 갱신
                events.update(
                    calendarId=cal_id, eventId=eid, body={**body, "status": "confirmed"}
                ).execute()
                updated += 1
        else:
            old_hash = cur.get("extendedProperties", {}).get("private", {}).get(HASH_KEY)
            if old_hash != body["extendedProperties"]["private"][HASH_KEY]:
                events.update(calendarId=cal_id, eventId=eid, body=body).execute()
                updated += 1

    for eid in dst.keys() - src.keys():
        try:
            events.delete(calendarId=cal_id, eventId=eid).execute()
            deleted += 1
        except HttpError as e:
            if e.resp.status not in (404, 410):
                raise

    print(f"created={created} updated={updated} deleted={deleted}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # 공개 로그에 URL·일정 내용이 남지 않도록 요약만 출력
        if os.environ.get("DEBUG") == "1":
            traceback.print_exc()
        status = getattr(getattr(e, "resp", None), "status", "")
        print(f"error: {type(e).__name__} {status}".strip())
        sys.exit(1)
