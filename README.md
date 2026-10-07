# naver-gcal-sync

네이버 캘린더(CalDAV) 일정을 구글 캘린더 한 곳에 단방향으로 복사합니다. GitHub Actions가 10분마다 `sync.py`를 실행합니다.

## Secrets
- `NAVER_ID`, `NAVER_APP_PW`: 네이버 아이디, 애플리케이션 비밀번호
- `GCAL_ID`: 대상 구글 캘린더 ID (서비스 계정에 "일정 변경" 권한으로 공유)
- `GOOGLE_SA_JSON`: 서비스 계정 JSON 키 전체 (`gh secret set GOOGLE_SA_JSON < key.json`)
- `NAVER_CALENDARS`: 선택. 동기화할 네이버 캘린더 이름, 쉼표 구분. 비우면 전체
- `NAVER_ID2`, `NAVER_APP_PW2`, `NAVER_CALENDARS2`: 선택. 두 번째 네이버 계정(아내). `NAVER_ID2`가 있으면 함께 동기화

## 로컬 확인
```
pip install -r requirements.txt
python test_sync.py
DEBUG=1 python sync.py   # Actions에서는 DEBUG를 켜지 말 것 (public 로그)
```