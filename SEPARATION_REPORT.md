# 🎯 프로젝트 분리 완료 보고서

## 📊 변경 사항

### ✅ 완료된 작업

#### 1. **독립 데이터베이스 구조**
```
이전:
├── blackeagles.db    (웹사이트 + CLI 공유)

현재:
├── blackeagles.db         (웹사이트 전용)
└── flight_schedules.db    (CLI 프로그램 전용, 자동 생성)
```

#### 2. **schedule.py 수정 사항**
- **Line 16**: `db_path='blackeagles.db'` → `db_path='flight_schedules.db'`
- **Line 19**: `_initialize_database()` 메서드 추가 (자동 테이블 생성)
- **Line 40-64**: 독립 데이터베이스 초기화 로직 구현

```python
def _initialize_database(self):
    """데이터베이스 초기화 - 테이블 생성"""
    # schedules 테이블 자동 생성
    # 웹사이트 DB 의존성 제거
```

#### 3. **app.py 복구**
- **Line 608-617**: 필터/D-Day 계산 로직 제거 → 단순 쿼리로 복구
- 웹사이트는 관리자 페이지에서만 일정 관리
- `/schedule` 페이지는 단순 목록 표시

#### 4. **템플릿 복구**
```bash
templates/schedule_old.html → templates/schedule.html (복구)
templates/schedule.html → templates/schedule_advanced.html (백업)
```

---

## 🔄 시스템 구조

### 📱 웹사이트 (app.py + blackeagles.db)
- **목적**: 공식 홈페이지
- **관리 방법**: 브라우저 관리자 페이지
- **URL**: http://127.0.0.1:5001
- **일정 페이지**: `/schedule` (단순 목록 표시)
- **관리**: `/admin/schedules` (추가/수정/삭제)
- **데이터베이스**: blackeagles.db

### 💻 CLI 프로그램 (schedule.py + flight_schedules.db)
- **목적**: 터미널 기반 스케줄 관리 도구
- **실행 방법**: `.venv/bin/python schedule.py`
- **주요 기능**:
  - ✅ D-Day 자동 계산 (D-15, D-Day, D+7)
  - ✅ 5가지 필터 (전체/다가오는/지난/이번주/이번달)
  - ✅ 키워드 검색 (제목/장소/설명)
  - ✅ 통계 (전체/다가오는/지난 일정 수)
  - ✅ Tabulate 테이블 포맷팅
- **데이터베이스**: flight_schedules.db (자동 생성)

---

## 📝 사용 가이드

### CLI 프로그램 실행
```bash
# 방법 1: 가상환경 사용 (권장)
cd /Users/jangseungha/Documents/블랙이글홈페이지
source .venv/bin/activate
python schedule.py

# 방법 2: 직접 경로 지정
.venv/bin/python schedule.py

# 방법 3: 전역 Python (tabulate 설치 필요)
pip3 install tabulate
python3 schedule.py
```

### 웹사이트 실행
```bash
cd /Users/jangseungha/Documents/블랙이글홈페이지
python3 app.py
# http://127.0.0.1:5001 접속
```

---

## 📂 파일 구조

```
블랙이글홈페이지/
│
├── app.py                      # Flask 웹 애플리케이션
├── schedule.py                 # CLI 스케줄 관리 프로그램
│
├── blackeagles.db              # 웹사이트 데이터베이스
├── flight_schedules.db         # CLI 프로그램 데이터베이스 (자동 생성)
│
├── templates/
│   ├── schedule.html           # 웹사이트 일정 페이지 (단순)
│   ├── schedule_advanced.html  # 고급 버전 (백업, 미사용)
│   └── admin/
│       └── schedules.html      # 관리자 일정 관리
│
└── 문서/
    ├── RUN_SCHEDULE.md         # CLI 프로그램 실행 가이드 (NEW!)
    ├── SCHEDULE_GUIDE.md       # CLI 프로그램 사용 가이드
    └── README_NEW.md           # 전체 프로젝트 문서
```

---

## 🎯 용도 구분

| 기능 | 웹사이트 | CLI 프로그램 |
|------|----------|--------------|
| **대상 사용자** | 일반 방문자 | 관리자/팀원 |
| **접근 방법** | 브라우저 | 터미널 |
| **일정 표시** | 기본 목록 | D-Day 포함 상세 정보 |
| **필터링** | ❌ | ✅ (5가지) |
| **검색** | ❌ | ✅ |
| **통계** | ❌ | ✅ |
| **데이터 동기화** | ❌ (독립) | ❌ (독립) |

---

## ⚠️ 중요 사항

1. **데이터베이스 독립성**
   - 웹사이트와 CLI 프로그램의 데이터는 **완전히 독립**
   - 한쪽에서 추가/수정/삭제해도 다른 쪽에 영향 없음

2. **실행 환경**
   - CLI 프로그램: 가상환경에서 실행 (`.venv/bin/python`)
   - 웹사이트: 전역 Python으로 실행 (`python3`)

3. **파일 생성**
   - `flight_schedules.db`는 프로그램 최초 실행 시 자동 생성
   - 수동으로 생성할 필요 없음

---

## 🚀 다음 단계 (선택사항)

만약 두 시스템을 나중에 연동하고 싶다면:

### 옵션 1: 데이터 동기화 스크립트
```python
# sync_schedules.py
# CLI → 웹사이트 또는 웹사이트 → CLI 데이터 복사
```

### 옵션 2: 공유 모드 추가
```python
# schedule.py에 --db 옵션 추가
python schedule.py --db blackeagles.db  # 웹사이트 DB 직접 관리
```

### 옵션 3: API 연동
```python
# CLI 프로그램에서 웹사이트 API 호출
```

---

## ✅ 테스트 결과

- ✅ CLI 프로그램 정상 실행 (독립 DB 생성)
- ✅ 웹사이트 정상 실행 (기존 DB 사용)
- ✅ 두 시스템 동시 실행 가능
- ✅ 데이터 충돌 없음
- ✅ 문서화 완료 (RUN_SCHEDULE.md)

**분리 작업 완료! 🎉**
