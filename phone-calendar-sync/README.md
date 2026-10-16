# 휴대폰 캘린더 → 공유 구글 캘린더 (MacroDroid + Apps Script)

## 왜 필요한가
롯데시네마 예매를 삼성 월렛에 등록하면 영화 일정이 삼성 캘린더에 자동으로 생긴다. 그런데 이 일정은 동기화되지 않는 삼성 기기 내부 캘린더("내 캘린더")에 저장된다. 그래서 구글 캘린더와 연동해 두어도 나만 보이고, 아내 캘린더에는 나타나지 않는다.

## 구조
```
휴대폰 캘린더 (삼성 "내 캘린더" 등)
  → MacroDroid가 읽음 (Get Calendar Events)
  → JSON으로 Apps Script 웹 앱에 POST
  → Apps Script가 공유 구글 캘린더에 일정 생성 (중복은 건너뜀)
```
- Apps Script 코드: [`apps-script.gs`](apps-script.gs)
- 이 저장소에는 실제 캘린더 ID, TOKEN, 웹 앱 URL을 넣지 않는다. 실제 값은 Apps Script 편집기와 MacroDroid 안에만 있다.

## 설정 순서

### 1. 공유 캘린더 (PC)
1. Google 캘린더에서 아내와 함께 볼 캘린더를 정한다. 없으면 "다른 캘린더 +" → 새 캘린더 만들기로 만든다.
2. 그 캘린더 설정 → 특정 사용자와 공유 → 아내 계정을 추가한다. 권한은 "일정 보기" 이상.
3. 설정 → 캘린더 통합 → **캘린더 ID**를 복사한다.

### 2. Apps Script (PC)
1. https://script.google.com 에서 새 프로젝트를 만들고 [`apps-script.gs`](apps-script.gs) 내용을 붙여 넣는다.
2. `CAL_ID`에 캘린더 ID를, `TOKEN`에 긴 랜덤 문자열을 넣는다.
3. ⚙ 프로젝트 설정 → 시간대를 **(GMT+09:00) 서울**로 바꾼다.
4. 배포 → 새 배포 → 유형 **웹 앱**, 실행 주체 **나**, 액세스 **모든 사용자** → 배포.
   - MacroDroid는 구글 로그인을 할 수 없어서 "모든 사용자"로 연다. 대신 `TOKEN`이 무단 요청을 막는다.
5. 권한을 허용한다. "확인되지 않은 앱" 경고가 나오면 고급 → 이동 → 허용.
6. `.../exec`로 끝나는 **웹 앱 URL**을 복사한다.
7. 나중에 코드를 고치면 배포 → 배포 관리 → ✏ 수정 → 버전 "새 버전" → 배포를 해야 반영된다. URL은 그대로다.

### 3. MacroDroid 매크로 (휴대폰)
MacroDroid 5.58.7 이상이 필요하다 (`Get Calendar Events` 액션).

- **로컬 변수**
  - `events`: 배열
  - `eventsJson`: 문자열
  - `result`: 문자열
- **트리거** (하나만 발생해도 실행된다)
  - 사용 중: 삼성 캘린더 앱 실행 시 (`Application Launched`)
  - 추가 권장: 삼성 월렛 종료 시 (`Application Closed`). 월렛에 등록만 하고 캘린더를 열지 않으면 동기화되지 않는 빈틈을 메운다.
- **액션**
  0. (월렛 종료 트리거를 쓸 때) `Wait Before Next Action` 10초. 월렛이 캘린더에 일정을 쓸 시간을 준다.
  1. `Get Calendar Events`
     - 캘린더: 삼성 "내 캘린더"
     - Start Offset: 0 Days
     - Duration: 60 Days
     - 출력: `events`
  2. `JSON Output`: `events`를 `eventsJson`으로 바꾼다.
  3. `HTTP Request`
     - 메서드: `POST`
     - URL: `<웹앱URL>?token=<TOKEN>`
     - Body: `{v=eventsJson}`, Content type `application/json`
     - 응답 저장: `result`
- 다른 캘린더도 복사하려면 1~3을 한 세트 더 넣는다. `Get Calendar Events`는 캘린더를 하나만 고를 수 있다.
- 아래 두 캘린더는 절대 넣지 않는다.
  - 진짜 개인용 private 캘린더
  - 공유 캘린더 자신 (자기 자신을 다시 복사하게 됨)

### 4. 갤럭시 배터리 설정
- 설정 → 애플리케이션 → MacroDroid → 배터리 → **제한 없음**
- 설정 → 배터리 → 백그라운드 사용 제한 → **절전 예외 앱**에 MacroDroid를 추가한다.

## 테스트와 확인
1. 임시로 `Popup Message`를 넣고 내용을 `{v=result}`로 둔 뒤, 매크로를 직접 실행한다.
2. 응답 저장이 **상태 코드**로 되어 있으면 팝업에 `200`이 뜬다. 요청이 도착했다는 뜻일 뿐, 성공 확정은 아니다. Apps Script는 스크립트 오류에도 200을 돌려줄 수 있다.
   - **응답 본문**을 저장하도록 바꾸면 `created N`이 보인다.
3. 성공 기준
   - 공유 캘린더에 일정이 생긴다.
   - 다시 실행해도 같은 일정이 늘지 않는다 (`created 0`).
4. 문제가 있을 때
   - `forbidden`이 뜨면 URL의 token과 스크립트의 `TOKEN`이 다르다.
   - 그 밖의 오류는 Apps Script 왼쪽 **실행** 메뉴의 로그를 본다.

현재 상태: 캘린더 앱 실행 트리거로 첫 실행 성공 (팝업 200). 공유 캘린더 반영과 중복 없음은 확인 필요.

## 한계
- **수정과 삭제는 반영되지 않는다.** 시간을 바꾸면 공유 캘린더에 새 일정이 하나 더 생기고, 이전 일정은 남는다. 예매를 취소하면 공유 캘린더에서 직접 지운다.
- **트리거가 발생할 때만 동기화된다.** 캘린더를 열거나 월렛을 닫아야 반영된다.
- 매번 60일 치를 보낸다. 중복은 Apps Script가 걸러 낸다.

## 참고: MacroDroid에서 확인한 사실
- 기본 `Calendar - Add Event`도 magic text로 정확한 시각을 넣을 수 있다. 하지만 중복 방지 기능이 없어서 주기적인 복사에는 맞지 않는다.
- `Get Calendar Events`의 일정 필드
  - `Title`, `Location`
  - `Start Timestamp`, `End Timestamp` (밀리초)
  - `All day event`
- MacroDroid 위키는 Cloudflare 때문에 일부 도구에서 403이 난다. 브라우저 User-Agent를 넣은 `curl`로는 열린다.
- 출처
  - [Get Calendar Events](https://wiki.macrodroid.com/wiki/index.php?title=Action:_Get_Calendar_Events)
  - [Calendar - Add Event](https://wiki.macrodroid.com/wiki/index.php?title=Action:_Calendar_-_Add_Event)
  - [Trigger: Calendar Event](https://wiki.macrodroid.com/wiki/index.php?title=Trigger:_Calendar_Event)
