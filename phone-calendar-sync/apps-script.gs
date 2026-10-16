// MacroDroid가 보낸 휴대폰 캘린더 일정을 공유 구글 캘린더에 만든다.
// 같은 제목 + 같은 시작(종일이면 같은 날짜) 일정이 이미 있으면 건너뛴다.
// 실제 값은 Apps Script 편집기에서만 채우고, 이 저장소에는 넣지 않는다.
const CAL_ID = '여기에_캘린더ID@group.calendar.google.com';
const TOKEN  = '여기에_긴_랜덤_문자열';
const TZ = 'Asia/Seoul';

function doPost(e) {
  if (e.parameter.token !== TOKEN) return out('forbidden');
  const cal = CalendarApp.getCalendarById(CAL_ID);
  const list = JSON.parse(e.postData.contents);
  let made = 0;
  for (const ev of list) {
    const title = ev['Title'] || '(제목 없음)';
    const start = new Date(Number(ev['Start Timestamp']));
    const end   = new Date(Number(ev['End Timestamp']));
    const allDay = String(ev['All day event']) === 'true';
    const day = d => Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
    const dup = cal.getEventsForDay(start).some(x => x.getTitle() === title &&
      (allDay ? x.isAllDayEvent() && day(x.getStartTime()) === day(start)
              : x.getStartTime().getTime() === start.getTime()));
    if (dup) continue;
    const opt = { location: ev['Location'] || '' };
    if (allDay) cal.createAllDayEvent(title, start, end, opt);
    else cal.createEvent(title, start, end, opt);
    made++;
  }
  return out('created ' + made);
}
const out = s => ContentService.createTextOutput(s);
