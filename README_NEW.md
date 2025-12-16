# Virtual Black Eagles - 홈페이지 & 스케줄 관리 시스템

가상 블랙이글스 팀의 공식 홈페이지와 비행 스케줄 관리 시스템입니다.

## 🚀 주요 기능

### 웹사이트 (Flask)
- **홈페이지**: 팀 소개 및 최신 소식
- **공지사항**: 게시판 형식의 공지사항
- **일정 관리**: 에어쇼 및 비행 일정
- **팀 소개**: 조종사, 전대장 인사말
- **갤러리**: 사진 게시판
- **문의하기**: 이메일 문의 폼
- **관리자 페이지**: 모든 콘텐츠 관리

### 비행 스케줄 관리 (CLI)
- **일정 CRUD**: 추가, 조회, 수정, 삭제
- **스마트 필터**: 오늘/이번 주/이번 달/다가오는/지난 일정
- **D-Day 계산**: 자동 D-Day 표시
- **검색 기능**: 제목, 장소, 설명 검색
- **통계**: 일정 현황 요약

## 📦 설치 및 실행

### 1. 가상환경 설정
```bash
# 저장소 클론 또는 디렉토리 이동
cd /Users/jangseungha/Documents/블랙이글홈페이지

# 가상환경 생성 (권장)
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 웹사이트 실행
```bash
# 데이터베이스 초기화 (처음 실행 시)
python3 -c "from app import init_db; init_db()"

# Flask 서버 시작
python3 app.py

# 또는 포트 지정
PORT=5001 python3 app.py
```

브라우저에서 http://127.0.0.1:5001 접속

### 3. 비행 스케줄 관리 프로그램 실행
```bash
# CLI 프로그램 실행
python3 schedule.py

# 또는 가상환경에서
.venv/bin/python schedule.py
```

자세한 사용법은 [SCHEDULE_GUIDE.md](SCHEDULE_GUIDE.md) 참조

## 📁 프로젝트 구조

```
블랙이글홈페이지/
├── app.py                  # Flask 메인 애플리케이션 (2,041줄)
├── schedule.py             # 비행 스케줄 관리 CLI 프로그램
├── blackeagles.db          # SQLite 데이터베이스
├── requirements.txt        # Python 의존성
├── README.md               # 프로젝트 문서 (본 파일)
├── SCHEDULE_GUIDE.md       # 스케줄 프로그램 사용 가이드
├── static/
│   ├── style.css          # 스타일시트 (826줄)
│   ├── script.js          # JavaScript
│   ├── images/            # 이미지 파일
│   ├── members/           # 팀원 사진
│   └── Picture/           # 기타 사진
└── templates/
    ├── base.html          # 기본 레이아웃 (한국어)
    ├── base_en.html       # 기본 레이아웃 (영어)
    ├── index.html         # 홈페이지
    ├── notice.html        # 공지사항
    ├── about.html         # 팀 소개
    ├── schedule.html      # 일정
    ├── contact.html       # 문의
    ├── gallery.html       # 갤러리
    └── admin/             # 관리자 페이지 (27개 파일)
```

## 🗄️ 데이터베이스

**파일**: `blackeagles.db` (SQLite3)

**주요 테이블**:
- `notices` - 공지사항
- `schedules` - 일정
- `pilots` - 조종사 정보
- `commander_greeting` - 전대장 인사말
- `contact_messages` - 문의 메시지
- `gallery` - 사진 게시판
- `banner_settings` - 배너 설정
- `page_sections` - 페이지 섹션
- `home_contents` - 홈 콘텐츠
- `about_sections` - 팀소개 섹션
- `site_images` - 사이트 이미지

## 🔐 관리자 페이지

**URL**: http://127.0.0.1:5001/admin

**관리 기능**:
- 공지사항 관리
- 일정 관리
- 조종사 관리
- 전대장 인사말 관리
- 갤러리 관리
- 문의 관리
- 배너 설정
- 페이지 콘텐츠 관리

## 🛠️ 기술 스택

- **Backend**: Python 3.14, Flask 3.x
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Template Engine**: Jinja2
- **Email**: Flask-Mail (Naver SMTP)
- **CLI Libraries**: tabulate

## 📊 비행 스케줄 관리 (schedule.py)

CLI 기반 비행 일정 관리 프로그램

**주요 명령**:
1. 일정 목록 조회 (전체/다가오는/지난/오늘/이번 주/이번 달)
2. 일정 추가
3. 일정 검색
4. 일정 상세 조회
5. 일정 수정
6. 일정 삭제
7. 통계

**특징**:
- D-Day 자동 계산
- 표 형식 출력 (tabulate)
- 날짜 자동 검증
- 한글 완벽 지원

**사용 예시**:
```bash
$ python3 schedule.py

✈️  Virtual Black Eagles - 비행 스케줄 관리
1. 📋 일정 목록 조회
2. ➕ 일정 추가
...

선택: 2
제목: 12월 연습 비행
장소: 공군 기지
날짜: 2025-12-20
설명: T-50B 8기 편대비행

✅ 일정이 추가되었습니다
```

자세한 사용법: [SCHEDULE_GUIDE.md](SCHEDULE_GUIDE.md)

## ⚙️ 환경 설정

### 메일 설정 (선택)
```bash
# set_mail_env.sh 파일 생성
export MAIL_SERVER=smtp.naver.com
export MAIL_PORT=587
export MAIL_USE_TLS=True
export MAIL_USERNAME=your_email@naver.com
export MAIL_PASSWORD=your_password

# 환경 변수 로드
source set_mail_env.sh
```

### 포트 설정
```bash
# 기본 포트: 5001
python3 app.py

# 커스텀 포트
PORT=8080 python3 app.py
```

## 📝 최적화 완료 사항

- ✅ CSS 중복 코드 제거 (19줄 감소)
- ✅ 템플릿 상속 구조 (base.html)
- ✅ 데이터베이스 정규화
- ✅ 코드 구조 개선
- ✅ 주석 추가

## 🐛 문제 해결

### 포트 충돌
macOS에서 5000번 포트가 사용 중일 경우:
```bash
PORT=5001 python3 app.py
```

### 데이터베이스 초기화
```bash
python3 -c "from app import init_db; init_db()"
```

### 한글 깨짐 (schedule.py)
```bash
export LANG=ko_KR.UTF-8
python3 schedule.py
```

## 📖 추가 문서

- [비행 스케줄 관리 가이드](SCHEDULE_GUIDE.md)

## 🔄 업데이트 내역

### v2.0 (2025-12-09)
- ✨ 비행 스케줄 관리 CLI 프로그램 추가
- ✨ 전대장 인사말 관리 기능 추가
- 🎨 CSS 중복 코드 제거 및 최적화
- 📝 문서화 개선

### v1.0 (2025-12)
- 🎉 초기 릴리즈
- 웹사이트 기본 기능 구현
- 관리자 페이지 구현

## 👥 개발팀

**프로젝트**: Virtual Black Eagles
**개발자**: Black Eagles Development Team

## 📄 라이선스

본 프로젝트는 Virtual Black Eagles 팀의 내부 프로젝트입니다.

---

**서버 주소**: http://127.0.0.1:5001  
**관리자**: http://127.0.0.1:5001/admin  
**문의**: rr3340@naver.com
