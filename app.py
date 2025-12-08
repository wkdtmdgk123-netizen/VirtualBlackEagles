import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
from functools import wraps


app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'devsecret-change-this-in-production')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Jinja2 필터 추가
@app.template_filter('youtube_embed')
def youtube_embed_filter(url):
	"""YouTube URL을 embed URL로 변환"""
	if not url:
		return url
	
	# 이미 embed URL인 경우
	if 'youtube.com/embed/' in url:
		return url
	
	# 일반 YouTube URL 변환
	if 'youtube.com/watch' in url:
		video_id = url.split('v=')[1].split('&')[0] if 'v=' in url else None
		if video_id:
			return f'https://www.youtube.com/embed/{video_id}'
	
	# 단축 URL 변환
	if 'youtu.be/' in url:
		video_id = url.split('youtu.be/')[1].split('?')[0]
		return f'https://www.youtube.com/embed/{video_id}'
	
	return url

# 데이터베이스 설정
DATABASE = 'blackeagles.db'

def get_db():
	"""데이터베이스 연결"""
	conn = sqlite3.connect(DATABASE)
	conn.row_factory = sqlite3.Row
	return conn

def init_db():
	"""데이터베이스 초기화"""
	conn = get_db()
	cursor = conn.cursor()
	
	# 공지사항 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS notices (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			content TEXT NOT NULL,
			author TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 일정 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS schedules (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			location TEXT,
			event_date DATE NOT NULL,
			description TEXT,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 문의 메시지 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS contact_messages (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT,
			email TEXT NOT NULL,
			message TEXT NOT NULL,
			type TEXT DEFAULT 'contact',
			is_read INTEGER DEFAULT 0,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 페이지 섹션 테이블 (개선된 버전)
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS page_sections (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			page_name TEXT NOT NULL,
			section_id TEXT NOT NULL,
			section_type TEXT NOT NULL,
			title TEXT,
			content TEXT,
			image_url TEXT,
			link_url TEXT,
			link_text TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(page_name, section_id)
		)
	''')
	
	# 기본 페이지 섹션 생성
	default_sections = [
		('home', 'about', 'text', 'About Us', '가상블랙이글스는 대한민국 블랙이글스의 다양한 특수비행을 통해 고도의 비행기량을 뽐내는 대한민국 가상 특수비행팀입니다.', None, None, None, 1, 1),
		('about', 'intro', 'text', '팀 소개', '블랙이글스는 대한민국 공군의 자랑입니다.', None, None, None, 1, 1),
		('contact', 'discord', 'text', 'Contact Us', 'Discord ㅣ Johnson#4553', None, None, None, 1, 1),
	]
	
	for section in default_sections:
		cursor.execute('''
			INSERT OR IGNORE INTO page_sections 
			(page_name, section_id, section_type, title, content, image_url, link_url, link_text, order_num, is_active)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		''', section)
	
	# 배너 설정 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS banner_settings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			page_name TEXT UNIQUE NOT NULL,
			background_image TEXT,
			title TEXT NOT NULL,
			subtitle TEXT,
			description TEXT,
			button_text TEXT,
			button_link TEXT,
			title_font TEXT DEFAULT 'Arial, sans-serif',
			title_color TEXT DEFAULT '#ffffff',
			subtitle_color TEXT DEFAULT '#ffffff',
			description_color TEXT DEFAULT '#ffffff',
			vertical_position TEXT DEFAULT 'center',
			padding_top INTEGER DEFAULT 250,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기존 테이블에 컬럼 추가 (이미 있으면 무시)
	try:
		cursor.execute('ALTER TABLE banner_settings ADD COLUMN vertical_position TEXT DEFAULT "center"')
	except:
		pass
	try:
		cursor.execute('ALTER TABLE banner_settings ADD COLUMN padding_top INTEGER DEFAULT 250')
	except:
		pass
	
	# 기본 홈페이지 배너 설정
	cursor.execute('''
		INSERT OR IGNORE INTO banner_settings (page_name, background_image, title, subtitle, description, button_text, button_link)
		VALUES ('home', '/static/images/hero.jpg', 'Black Eagles', 'Republic Of Korea AirForce', 
		        '가상블랙이글스는 대한민국 블랙이글스의 다양한 특수비행을 통해 고도의 비행기량을 뽐내는 대한민국 가상 특수비행팀입니다.', 
		        'more', '#about')
	''')
	
	# 조종사 정보 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS pilots (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			number INTEGER NOT NULL,
			position TEXT NOT NULL,
			callsign TEXT NOT NULL,
			generation TEXT NOT NULL,
			aircraft TEXT NOT NULL,
			photo_url TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 조종사 데이터 삽입 (중복 방지)
	default_pilots = [
		(1, 'LEADER', 'Bulta', 'VBE 1기', 'F-5', '/static/members/moon.jpeg', 1, 1),
		(2, 'LEFT WING', 'Fox9', 'VBE 2기', 'F-18', '/static/members/moon.jpeg', 2, 1),
		(3, 'RIGHT WING', 'Ace', 'VBE 1기', 'F-18', '/static/members/moon.jpeg', 3, 1),
		(4, 'Slot', 'Moon', 'VBE 1기', 'F-5', '/static/members/moon.jpeg', 4, 1),
		(5, 'SYNCHRO-1', 'ZeroDistance', 'VBE 1기', 'F-5', '/static/members/moon.jpeg', 5, 1),
		(6, 'SYNCHRO-2', 'Lewis', 'VBE 1기', 'F-5', '/static/members/Lewis.jpg', 6, 1),
		(7, 'SOLO-1', 'Sonic', 'VBE 1기', 'F-5', '/static/members/moon.jpeg', 7, 1),
		(8, 'SOLO-2', 'Strike', 'VBE 1기', 'F-5', '/static/members/moon.jpeg', 8, 1),
	]
	
	# 이미 데이터가 있는지 확인
	existing_count = cursor.execute('SELECT COUNT(*) FROM pilots').fetchone()[0]
	
	# 데이터가 없을 때만 기본 데이터 삽입
	if existing_count == 0:
		for pilot in default_pilots:
			cursor.execute('''
				INSERT INTO pilots 
				(number, position, callsign, generation, aircraft, photo_url, order_num, is_active)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			''', pilot)
	
	# 홈 콘텐츠 테이블 (유튜브, SNS 피드 등)
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS home_contents (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			content_type TEXT NOT NULL,
			title TEXT,
			content_data TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 유튜브 콘텐츠 삽입
	cursor.execute('''
		INSERT OR IGNORE INTO home_contents (id, content_type, title, content_data, order_num, is_active)
		VALUES (1, 'youtube', 'Latest Video', 'https://www.youtube.com/embed/dQw4w9WgXcQ', 1, 1)
	''')
	
	# 팀소개 섹션 테이블 (개요, 항공기 등)
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS about_sections (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			section_type TEXT NOT NULL,
			title TEXT,
			content TEXT,
			image_url TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 개요 섹션 추가
	cursor.execute('''
		INSERT OR IGNORE INTO about_sections (id, section_type, title, content, order_num, is_active)
		VALUES (1, 'overview', '가상 블랙이글스 소개', 
		'가상 블랙이글스는 DCS World에서 활동하는 대한민국 가상 공군 특수비행팀입니다. 실제 블랙이글스의 정신과 전통을 계승하며, 정교한 편대비행과 에어쇼를 통해 뛰어난 비행실력을 선보입니다.', 
		0, 1)
	''')
	
	cursor.execute('''
		INSERT OR IGNORE INTO about_sections (id, section_type, title, content, order_num, is_active)
		VALUES (2, 'mission', '임무', 
		'우리의 임무는 대한민국 공군의 우수성을 전 세계에 알리고, 가상 비행 시뮬레이션을 통해 항공에 대한 관심과 이해를 높이는 것입니다. 또한 팀원들의 비행 실력 향상과 팀워크 강화를 목표로 합니다.', 
		1, 1)
	''')
	
	cursor.execute('''
		INSERT OR IGNORE INTO about_sections (id, section_type, title, content, order_num, is_active)
		VALUES (3, 'aircraft_intro', 'T-50B 골든이글', 
		'T-50B는 대한민국이 자체 개발한 초음속 고등훈련기로, 블랙이글스 팀이 사용하는 항공기입니다. 우수한 기동성과 안정성을 자랑하며, 다양한 편대비행 기동을 수행할 수 있습니다.', 
		2, 1)
	''')
	
	cursor.execute('''
		INSERT OR IGNORE INTO about_sections (id, section_type, title, content, image_url, order_num, is_active)
		VALUES (4, 'aircraft_specs', 'T-50B 제원', 
		'최대속도: 마하 1.5|전투행동반경: 1,851km|최대이륙중량: 12,300kg|엔진: F404-GE-102 터보팬|승무원: 2명|무장: 20mm 기관포, 공대공 미사일',
		'/static/images/t50b.jpg', 
		3, 1)
	''')
	
	cursor.execute('''
		INSERT OR IGNORE INTO about_sections (id, section_type, title, content, order_num, is_active)
		VALUES (5, 'aircraft_features', '특징', 
		'우수한 기동성|높은 안정성|효율적인 연료 소비|조종사 친화적 설계|다목적 운용 가능', 
		4, 1)
	''')
	
	# 전대장 인사말 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS commander_greeting (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			rank TEXT NOT NULL,
			callsign TEXT NOT NULL,
			generation TEXT NOT NULL,
			aircraft TEXT NOT NULL,
			photo_url TEXT,
			greeting_text TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 전대장 데이터 삽입 (데이터가 없을 때만)
	existing_commanders = cursor.execute('SELECT COUNT(*) as count FROM commander_greeting').fetchone()[0]
	if existing_commanders == 0:
		cursor.execute('''
			INSERT INTO commander_greeting (name, rank, callsign, generation, aircraft, photo_url, greeting_text, order_num, is_active)
			VALUES ('Bulta', 'COMMANDER', '#1 Bulta', 'VBE 1기', 'F-5', '/static/images/default-pilot.jpg', 
			'안녕하십니까. 가상 블랙이글스 전대장입니다. 우리 팀은 대한민국 공군의 자랑스러운 전통을 계승하며, 최고의 비행 실력을 갖춘 정예 조종사들로 구성되어 있습니다.', 
			1, 1)
		''')

	# 정비사 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS maintenance_crew (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			role TEXT,
			callsign TEXT,
			photo_url TEXT,
			bio TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')

	# 후보자 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS candidates (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			callsign TEXT,
			photo_url TEXT,
			bio TEXT,
			order_num INTEGER DEFAULT 0,
			is_active INTEGER DEFAULT 1,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')

	# 사진 게시판 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS gallery (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			description TEXT,
			image_url TEXT NOT NULL,
			upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			is_active INTEGER DEFAULT 1,
			order_num INTEGER DEFAULT 0,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 샘플 이미지 추가
	cursor.execute('''
		INSERT OR IGNORE INTO gallery (id, title, description, image_url, order_num, is_active)
		VALUES (1, '편대비행 훈련', 'T-50B 4기 편대비행 훈련 모습', '/static/images/formation1.jpg', 1, 1)
	''')
	
	cursor.execute('''
		INSERT OR IGNORE INTO gallery (id, title, description, image_url, order_num, is_active)
		VALUES (2, '에어쇼 공연', '2024 서울 에어쇼 블랙이글스 공연', '/static/images/airshow1.jpg', 2, 1)
	''')
	
	# 사이트 이미지 관리 테이블
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS site_images (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			image_key TEXT UNIQUE NOT NULL,
			image_name TEXT NOT NULL,
			image_path TEXT NOT NULL,
			description TEXT,
			category TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 이미지 키 등록
	default_images = [
		('hero_banner', '홈 배너 이미지', '/static/images/hero.jpg', '메인 페이지 상단 배너', 'home'),
		('about_banner', '팀소개 배너 이미지', '/static/images/hero.jpg', '팀소개 페이지 상단 배너', 'about'),
		('default_pilot', '기본 파일럿 이미지', '/static/images/default-pilot.jpg', '파일럿 기본 프로필', 'about'),
		('t50b_main', 'T-50B 메인 이미지', '/static/images/t50b.jpg', '항공기 소개 이미지', 'about'),
	]
	
	for img_key, img_name, img_path, desc, cat in default_images:
		cursor.execute('''
			INSERT OR IGNORE INTO site_images (image_key, image_name, image_path, description, category)
			VALUES (?, ?, ?, ?, ?)
		''', (img_key, img_name, img_path, desc, cat))
	
	conn.commit()
	conn.close()

# 관리자 계정 (실제 운영시에는 데이터베이스나 환경변수 사용 권장)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'blackeagles2025')

# Flask-Mail configuration (set these as environment variables for security)
# Example for Naver SMTP:
#   export MAIL_SERVER=smtp.naver.com
#   export MAIL_PORT=465
#   export MAIL_USE_SSL=true
#   export MAIL_USERNAME=rr3340@naver.com
#   export MAIL_PASSWORD=your_app_password
#   export MAIL_DEFAULT_SENDER=rr3340@naver.com

# Gmail 설정 (실제 사용시 네이버 앱 비밀번호로 변경하세요)
# Gmail을 사용하려면 아래 주석을 해제하고 네이버 설정을 주석 처리하세요
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
# app.config['MAIL_PASSWORD'] = 'your-app-password'

# 네이버 메일 설정
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.naver.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'true').lower() == 'true'
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'rr3340@naver.com')  # 기본값 설정
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # 여기에 네이버 앱 비밀번호 입력
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'rr3340@naver.com')

mail = Mail(app)

@app.route('/send_mail', methods=['POST'])
def send_mail():
	name = request.form.get('name', '').strip()
	email = request.form.get('email', '').strip()
	message = request.form.get('message', '').strip()
	
	if not email or not message:
		flash('이메일과 메시지를 모두 입력해 주세요.', 'error')
		return redirect(url_for('contact'))
	
	try:
		# 데이터베이스에 문의 내용 저장 (type은 'contact')
		conn = get_db()
		cursor = conn.cursor()
		cursor.execute('''
			INSERT INTO contact_messages (name, email, message, type)
			VALUES (?, ?, ?, ?)
		''', (name or '익명', email, message, 'contact'))
		conn.commit()
		conn.close()
		
		flash('문의가 성공적으로 접수되었습니다! 관리자가 확인 후 답변드리겠습니다.', 'success')
	except Exception as e:
		print(f"문의 저장 실패: {str(e)}")
		flash('문의 접수에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
	
	return redirect(url_for('contact'))


@app.route('/')
def index():
	lang = request.args.get('lang', 'ko')  # 기본값은 한국어
	conn = get_db()
	banner = conn.execute('SELECT * FROM banner_settings WHERE page_name = ?', ('home',)).fetchone()
	sections = conn.execute('SELECT * FROM page_sections WHERE page_name = ? AND is_active = 1 ORDER BY order_num', ('home',)).fetchall()
	home_contents = conn.execute('SELECT * FROM home_contents WHERE is_active = 1 ORDER BY order_num').fetchall()
	
	# 사이트 이미지 가져오기
	site_images = {}
	images = conn.execute('SELECT image_key, image_path FROM site_images').fetchall()
	for img in images:
		site_images[img['image_key']] = img['image_path']
	
	conn.close()
	
	# 언어 설정을 템플릿에 전달
	if lang == 'en':
		return render_template('index_en.html', banner=banner, sections=sections, home_contents=home_contents, site_images=site_images)
	else:
		return render_template('index.html', banner=banner, sections=sections, home_contents=home_contents, site_images=site_images)


@app.route('/notice')
def notice():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	notices = conn.execute('SELECT * FROM notices ORDER BY created_at DESC').fetchall()
	conn.close()
	
	if lang == 'en':
		return render_template('notice_en.html', notices=notices)
	else:
		return render_template('notice.html', notices=notices)


@app.route('/notice/<int:notice_id>')
def notice_detail(notice_id):
	conn = get_db()
	notice = conn.execute('SELECT * FROM notices WHERE id = ?', (notice_id,)).fetchone()
	conn.close()
	
	if not notice:
		flash('공지사항을 찾을 수 없습니다.', 'error')
		return redirect(url_for('notice'))
	
	return render_template('notice_detail.html', notice=notice)


@app.route('/about')
def about():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	banner = conn.execute('SELECT * FROM banner_settings WHERE page_name = ?', ('about',)).fetchone()
	sections = conn.execute('SELECT * FROM page_sections WHERE page_name = ? AND is_active = 1 ORDER BY order_num', ('about',)).fetchall()
	pilots = conn.execute('SELECT * FROM pilots WHERE is_active = 1 ORDER BY order_num').fetchall()
	
	# 정비사 가져오기
	maintenance_crew = conn.execute('SELECT * FROM maintenance_crew WHERE is_active = 1 ORDER BY order_num').fetchall()
	
	# 후보자 가져오기
	candidates = conn.execute('SELECT * FROM candidates WHERE is_active = 1 ORDER BY order_num').fetchall()
	
	# 전대장 인사말 가져오기 - 언어별로 가져오기
	lang_param = 'en' if lang == 'en' else 'ko'
	commanders = conn.execute('SELECT * FROM commander_greeting WHERE is_active = 1 AND lang = ? ORDER BY order_num', (lang_param,)).fetchall()
	
	# 개요 섹션 가져오기 (임무, 선발, 편대) - 언어별로 가져오기
	lang_param = 'en' if lang == 'en' else 'ko'
	overview_sections = conn.execute('SELECT * FROM about_sections WHERE section_type IN (?, ?, ?) AND is_active = 1 AND lang = ? ORDER BY order_num', ('mission', 'selection', 'formation', lang_param)).fetchall()
	
	# 사이트 이미지 가져오기
	site_images = {}
	images = conn.execute('SELECT image_key, image_path FROM site_images').fetchall()
	for img in images:
		site_images[img['image_key']] = img['image_path']
	
	conn.close()
	
	if lang == 'en':
		return render_template('about_en.html', banner=banner, sections=sections, pilots=pilots, maintenance_crew=maintenance_crew, candidates=candidates, commanders=commanders, overview_sections=overview_sections, site_images=site_images)
	else:
		return render_template('about.html', banner=banner, sections=sections, pilots=pilots, maintenance_crew=maintenance_crew, candidates=candidates, commanders=commanders, overview_sections=overview_sections, site_images=site_images)


@app.route('/contact')
def contact():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	banner = conn.execute('SELECT * FROM banner_settings WHERE page_name = ?', ('contact',)).fetchone()
	sections = conn.execute('SELECT * FROM page_sections WHERE page_name = ? AND is_active = 1 ORDER BY order_num', ('contact',)).fetchall()
	conn.close()
	
	if lang == 'en':
		return render_template('contact_en.html', banner=banner, sections=sections)
	else:
		return render_template('contact.html', banner=banner, sections=sections)


@app.route('/donate')
def donate():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	banner = conn.execute('SELECT * FROM banner_settings WHERE page_name = ?', ('donate',)).fetchone()
	sections = conn.execute('SELECT * FROM page_sections WHERE page_name = ? AND is_active = 1 ORDER BY order_num', ('donate',)).fetchall()
	conn.close()
	
	if lang == 'en':
		return render_template('donate_en.html', banner=banner, sections=sections)
	else:
		return render_template('donate.html', banner=banner, sections=sections)


@app.route('/gallery')
def gallery():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	photos = conn.execute('SELECT * FROM gallery WHERE is_active = 1 ORDER BY order_num, upload_date DESC').fetchall()
	conn.close()
	
	if lang == 'en':
		return render_template('gallery_en.html', photos=photos)
	else:
		return render_template('gallery.html', photos=photos)


@app.route('/send_donate', methods=['POST'])
def send_donate():
	name = request.form.get('name', '').strip()
	amount = request.form.get('email', '').strip()  # email 필드를 금액으로 사용
	message = request.form.get('message', '').strip()
	
	if not amount or not message:
		flash('금액과 메시지를 모두 입력해 주세요.', 'error')
		return redirect(url_for('donate'))
	
	try:
		# 데이터베이스에 후원 문의 저장 (email 필드에 금액 저장, type은 'donate')
		conn = get_db()
		conn.execute(
			'INSERT INTO contact_messages (name, email, message, type) VALUES (?, ?, ?, ?)',
			(name, amount, message, 'donate')
		)
		conn.commit()
		conn.close()
		
		flash('후원 문의가 성공적으로 전송되었습니다! 빠른 시일 내에 연락드리겠습니다.', 'success')
		return redirect(url_for('donate'))
	
	except Exception as e:
		print(f"후원 문의 전송 오류: {str(e)}")
		flash('전송 중 오류가 발생했습니다. 다시 시도해 주세요.', 'error')
		return redirect(url_for('donate'))


@app.route('/schedule')
def schedule():
	lang = request.args.get('lang', 'ko')
	conn = get_db()
	schedules = conn.execute('SELECT * FROM schedules ORDER BY event_date DESC').fetchall()
	conn.close()
	
	if lang == 'en':
		return render_template('schedule_en.html', schedules=schedules)
	else:
		return render_template('schedule.html', schedules=schedules)
def schedule():
	conn = get_db()
	schedules = conn.execute('SELECT * FROM schedules ORDER BY event_date DESC').fetchall()
	conn.close()
	return render_template('schedule.html', schedules=schedules)


@app.route('/schedule/<int:schedule_id>')
def schedule_detail(schedule_id):
	conn = get_db()
	schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
	conn.close()
	
	if not schedule:
		flash('일정을 찾을 수 없습니다.', 'error')
		return redirect(url_for('schedule'))
	
	return render_template('schedule_detail.html', schedule=schedule)


# 로그인 체크 데코레이터
def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'logged_in' not in session:
			flash('로그인이 필요합니다.', 'error')
			return redirect(url_for('admin_login'))
		return f(*args, **kwargs)
	return decorated_function


# 관리자 로그인 페이지
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
	if request.method == 'POST':
		username = request.form.get('username', '').strip()
		password = request.form.get('password', '').strip()
		
		if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
			session['logged_in'] = True
			session['username'] = username
			flash('로그인 성공!', 'success')
			return redirect(url_for('admin_dashboard'))
		else:
			flash('아이디 또는 비밀번호가 잘못되었습니다.', 'error')
	
	return render_template('admin/login.html')


# 관리자 로그아웃
@app.route('/admin/logout')
def admin_logout():
	session.clear()
	flash('로그아웃되었습니다.', 'success')
	return redirect(url_for('index'))


# 관리자 대시보드
@app.route('/admin')
@login_required
def admin_dashboard():
	conn = get_db()
	# 읽지 않은 문의 수 가져오기
	unread_count = conn.execute('SELECT COUNT(*) as count FROM contact_messages WHERE is_read = 0').fetchone()['count']
	# 최근 문의 5개 가져오기
	recent_messages = conn.execute('SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 5').fetchall()
	conn.close()
	
	return render_template('admin/dashboard.html', unread_count=unread_count, recent_messages=recent_messages)


# 공지사항 관리 - 목록
@app.route('/admin/notices')
@login_required
def admin_notices():
	conn = get_db()
	notices = conn.execute('SELECT * FROM notices ORDER BY created_at DESC').fetchall()
	conn.close()
	return render_template('admin/notices.html', notices=notices)


# 공지사항 작성 페이지
@app.route('/admin/notices/new', methods=['GET', 'POST'])
@login_required
def admin_notice_new():
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		content = request.form.get('content', '').strip()
		author = session.get('username', 'admin')
		
		if not title or not content:
			flash('제목과 내용을 모두 입력해주세요.', 'error')
			return redirect(url_for('admin_notice_new'))
		
		conn = get_db()
		conn.execute('INSERT INTO notices (title, content, author) VALUES (?, ?, ?)',
					 (title, content, author))
		conn.commit()
		conn.close()
		
		flash('공지사항이 작성되었습니다.', 'success')
		return redirect(url_for('admin_notices'))
	
	return render_template('admin/notice_form.html', notice=None)


# 공지사항 수정 페이지
@app.route('/admin/notices/<int:notice_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_notice_edit(notice_id):
	conn = get_db()
	
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		content = request.form.get('content', '').strip()
		
		if not title or not content:
			flash('제목과 내용을 모두 입력해주세요.', 'error')
			return redirect(url_for('admin_notice_edit', notice_id=notice_id))
		
		conn.execute('UPDATE notices SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
					 (title, content, notice_id))
		conn.commit()
		conn.close()
		
		flash('공지사항이 수정되었습니다.', 'success')
		return redirect(url_for('admin_notices'))
	
	notice = conn.execute('SELECT * FROM notices WHERE id = ?', (notice_id,)).fetchone()
	conn.close()
	
	if not notice:
		flash('공지사항을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_notices'))
	
	return render_template('admin/notice_form.html', notice=notice)


# 공지사항 삭제
@app.route('/admin/notices/<int:notice_id>/delete', methods=['POST'])
@login_required
def admin_notice_delete(notice_id):
	conn = get_db()
	conn.execute('DELETE FROM notices WHERE id = ?', (notice_id,))
	conn.commit()
	conn.close()
	
	flash('공지사항이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_notices'))


# 일정 관리 - 목록
@app.route('/admin/schedules')
@login_required
def admin_schedules():
	conn = get_db()
	schedules = conn.execute('SELECT * FROM schedules ORDER BY event_date DESC').fetchall()
	conn.close()
	return render_template('admin/schedules.html', schedules=schedules)


# 일정 작성 페이지
@app.route('/admin/schedules/new', methods=['GET', 'POST'])
@login_required
def admin_schedule_new():
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		location = request.form.get('location', '').strip()
		event_date = request.form.get('event_date', '').strip()
		description = request.form.get('description', '').strip()
		
		if not title or not event_date:
			flash('제목과 날짜를 모두 입력해주세요.', 'error')
			return redirect(url_for('admin_schedule_new'))
		
		conn = get_db()
		conn.execute('INSERT INTO schedules (title, location, event_date, description) VALUES (?, ?, ?, ?)',
					 (title, location, event_date, description))
		conn.commit()
		conn.close()
		
		flash('일정이 추가되었습니다.', 'success')
		return redirect(url_for('admin_schedules'))
	
	return render_template('admin/schedule_form.html', schedule=None)


# 일정 수정 페이지
@app.route('/admin/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_schedule_edit(schedule_id):
	conn = get_db()
	
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		location = request.form.get('location', '').strip()
		event_date = request.form.get('event_date', '').strip()
		description = request.form.get('description', '').strip()
		
		if not title or not event_date:
			flash('제목과 날짜를 모두 입력해주세요.', 'error')
			return redirect(url_for('admin_schedule_edit', schedule_id=schedule_id))
		
		conn.execute('UPDATE schedules SET title = ?, location = ?, event_date = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
					 (title, location, event_date, description, schedule_id))
		conn.commit()
		conn.close()
		
		flash('일정이 수정되었습니다.', 'success')
		return redirect(url_for('admin_schedules'))
	
	schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
	conn.close()
	
	if not schedule:
		flash('일정을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_schedules'))
	
	return render_template('admin/schedule_form.html', schedule=schedule)


# 일정 삭제
@app.route('/admin/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
def admin_schedule_delete(schedule_id):
	conn = get_db()
	conn.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
	conn.commit()
	conn.close()
	
	flash('일정이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_schedules'))


# 문의 관리 - 목록
@app.route('/admin/messages')
@login_required
def admin_messages():
	message_type = request.args.get('type', 'all')  # all, contact, donate
	conn = get_db()
	
	if message_type == 'contact':
		messages = conn.execute("SELECT * FROM contact_messages WHERE type = 'contact' OR type IS NULL ORDER BY created_at DESC").fetchall()
	elif message_type == 'donate':
		messages = conn.execute("SELECT * FROM contact_messages WHERE type = 'donate' ORDER BY created_at DESC").fetchall()
	else:  # all
		messages = conn.execute('SELECT * FROM contact_messages ORDER BY created_at DESC').fetchall()
	
	conn.close()
	
	return render_template('admin/messages.html', messages=messages, current_type=message_type)


# 문의 상세보기
@app.route('/admin/messages/<int:message_id>')
@login_required
def admin_message_detail(message_id):
	conn = get_db()
	message = conn.execute('SELECT * FROM contact_messages WHERE id = ?', (message_id,)).fetchone()
	
	if message and message['is_read'] == 0:
		# 읽음 표시
		conn.execute('UPDATE contact_messages SET is_read = 1 WHERE id = ?', (message_id,))
		conn.commit()
	
	conn.close()
	
	if not message:
		flash('문의를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_messages'))
	
	return render_template('admin/message_detail.html', message=message)


# 문의 삭제
@app.route('/admin/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def admin_message_delete(message_id):
	conn = get_db()
	conn.execute('DELETE FROM contact_messages WHERE id = ?', (message_id,))
	conn.commit()
	conn.close()
	
	flash('문의가 삭제되었습니다.', 'success')
	return redirect(url_for('admin_messages'))


# 페이지 섹션 관리
@app.route('/admin/pages')
@login_required
def admin_pages():
	conn = get_db()
	sections = conn.execute('SELECT * FROM page_sections ORDER BY page_name, order_num').fetchall()
	conn.close()
	
	# 페이지별로 그룹화
	pages = {}
	for section in sections:
		page = section['page_name']
		if page not in pages:
			pages[page] = []
		pages[page].append(section)
	
	return render_template('admin/pages.html', pages=pages)


# 페이지 섹션 추가/수정 폼
@app.route('/admin/pages/section', methods=['GET'])
@app.route('/admin/pages/section/<int:section_id>', methods=['GET'])
@login_required
def admin_page_section_form(section_id=None):
	section = None
	if section_id:
		conn = get_db()
		section = conn.execute('SELECT * FROM page_sections WHERE id = ?', (section_id,)).fetchone()
		conn.close()
		if not section:
			flash('섹션을 찾을 수 없습니다.', 'error')
			return redirect(url_for('admin_pages'))
	
	return render_template('admin/page_section_form.html', section=section)


# 페이지 섹션 저장
@app.route('/admin/pages/section/save', methods=['POST'])
@login_required
def admin_page_section_save():
	section_id = request.form.get('section_id', '').strip()
	page_name = request.form.get('page_name', '').strip()
	section_identifier = request.form.get('section_identifier', '').strip()
	section_type = request.form.get('section_type', 'text').strip()
	title = request.form.get('title', '').strip()
	content = request.form.get('content', '').strip()
	image_url = request.form.get('image_url', '').strip()
	link_url = request.form.get('link_url', '').strip()
	link_text = request.form.get('link_text', '').strip()
	order_num = request.form.get('order_num', '0').strip()
	is_active = 1 if request.form.get('is_active') == 'on' else 0
	
	if not page_name or not section_identifier:
		flash('페이지 이름과 섹션 ID는 필수입니다.', 'error')
		return redirect(url_for('admin_page_section_form'))
	
	conn = get_db()
	
	if section_id:
		# 업데이트
		conn.execute('''
			UPDATE page_sections 
			SET page_name = ?, section_id = ?, section_type = ?, title = ?, content = ?, 
			    image_url = ?, link_url = ?, link_text = ?, order_num = ?, is_active = ?, 
			    updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		''', (page_name, section_identifier, section_type, title, content, image_url, 
		      link_url, link_text, order_num, is_active, section_id))
		flash('섹션이 수정되었습니다.', 'success')
	else:
		# 새로 추가
		try:
			conn.execute('''
				INSERT INTO page_sections 
				(page_name, section_id, section_type, title, content, image_url, link_url, link_text, order_num, is_active)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			''', (page_name, section_identifier, section_type, title, content, image_url, 
			      link_url, link_text, order_num, is_active))
			flash('섹션이 추가되었습니다.', 'success')
		except sqlite3.IntegrityError:
			flash('이미 존재하는 페이지/섹션 조합입니다.', 'error')
			conn.close()
			return redirect(url_for('admin_page_section_form'))
	
	conn.commit()
	conn.close()
	return redirect(url_for('admin_pages'))


# 페이지 섹션 삭제
@app.route('/admin/pages/section/<int:section_id>/delete', methods=['POST'])
@login_required
def admin_page_section_delete(section_id):
	conn = get_db()
	conn.execute('DELETE FROM page_sections WHERE id = ?', (section_id,))
	conn.commit()
	conn.close()
	flash('섹션이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_pages'))


# 배너 설정 관리
@app.route('/admin/banner')
@login_required
def admin_banner():
	conn = get_db()
	banners = conn.execute('SELECT * FROM banner_settings ORDER BY page_name').fetchall()
	conn.close()
	return render_template('admin/banner.html', banners=banners)


# 배너 설정 수정
@app.route('/admin/banner/<int:banner_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_banner_edit(banner_id):
	conn = get_db()
	
	if request.method == 'POST':
		background_image = request.form.get('background_image', '').strip()
		title = request.form.get('title', '').strip()
		subtitle = request.form.get('subtitle', '').strip()
		description = request.form.get('description', '').strip()
		button_text = request.form.get('button_text', '').strip()
		button_link = request.form.get('button_link', '').strip()
		title_font = request.form.get('title_font', 'Arial, sans-serif').strip()
		title_color = request.form.get('title_color', '#ffffff').strip()
		subtitle_color = request.form.get('subtitle_color', '#ffffff').strip()
		description_color = request.form.get('description_color', '#ffffff').strip()
		vertical_position = request.form.get('vertical_position', 'center').strip()
		padding_top = request.form.get('padding_top', '250').strip()
		
		if not title:
			flash('제목을 입력해주세요.', 'error')
			return redirect(url_for('admin_banner_edit', banner_id=banner_id))
		
		try:
			padding_top_int = int(padding_top)
		except:
			padding_top_int = 250
		
		conn.execute('''
			UPDATE banner_settings 
			SET background_image = ?, title = ?, subtitle = ?, description = ?, 
			    button_text = ?, button_link = ?, title_font = ?, title_color = ?, 
			    subtitle_color = ?, description_color = ?, vertical_position = ?, 
			    padding_top = ?, updated_at = CURRENT_TIMESTAMP 
			WHERE id = ?
		''', (background_image, title, subtitle, description, button_text, button_link,
		      title_font, title_color, subtitle_color, description_color, vertical_position,
		      padding_top_int, banner_id))
		conn.commit()
		conn.close()
		
		flash('배너 설정이 수정되었습니다.', 'success')
		return redirect(url_for('admin_banner'))
	
	banner = conn.execute('SELECT * FROM banner_settings WHERE id = ?', (banner_id,)).fetchone()
	conn.close()
	
	if not banner:
		flash('배너 설정을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_banner'))
	
	return render_template('admin/banner_form.html', banner=banner)


# 조종사 관리
@app.route('/admin/pilots')
@login_required
def admin_pilots():
	conn = get_db()
	pilots = conn.execute('SELECT * FROM pilots ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/pilots.html', pilots=pilots)


# 조종사 추가
@app.route('/admin/pilots/new', methods=['GET', 'POST'])
@login_required
def admin_pilot_new():
	if request.method == 'POST':
		number = request.form.get('number', '').strip()
		position = request.form.get('position', '').strip()
		callsign = request.form.get('callsign', '').strip()
		generation = request.form.get('generation', '').strip()
		aircraft = request.form.get('aircraft', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([number, position, callsign, generation, aircraft]):
			flash('모든 필수 항목을 입력해주세요.', 'error')
			return redirect(url_for('admin_pilot_new'))
		
		try:
			number_int = int(number)
			order_num_int = int(order_num)
		except:
			flash('번호와 정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_pilot_new'))
		
		# 파일 업로드 처리
		photo_url = '/static/images/default-pilot.jpg'  # 기본 이미지
		file = request.files.get('photo')
		if file and file.filename:
			filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_pilot_{callsign}_{file.filename}"
			filepath = os.path.join('static', 'members', filename)
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			file.save(filepath)
			photo_url = f'/static/members/{filename}'
		
		conn = get_db()
		conn.execute('''
			INSERT INTO pilots (number, position, callsign, generation, aircraft, photo_url, order_num, is_active)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		''', (number_int, position, callsign, generation, aircraft, photo_url, order_num_int, is_active))
		conn.commit()
		conn.close()
		
		flash('조종사가 추가되었습니다.', 'success')
		return redirect(url_for('admin_pilots'))
	
	return render_template('admin/pilot_form.html', pilot=None)


# 조종사 수정
@app.route('/admin/pilots/<int:pilot_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_pilot_edit(pilot_id):
	conn = get_db()
	
	if request.method == 'POST':
		number = request.form.get('number', '').strip()
		position = request.form.get('position', '').strip()
		callsign = request.form.get('callsign', '').strip()
		generation = request.form.get('generation', '').strip()
		aircraft = request.form.get('aircraft', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([number, position, callsign, generation, aircraft]):
			flash('모든 필수 항목을 입력해주세요.', 'error')
			return redirect(url_for('admin_pilot_edit', pilot_id=pilot_id))
		
		try:
			number_int = int(number)
			order_num_int = int(order_num)
		except:
			flash('번호와 정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_pilot_edit', pilot_id=pilot_id))
		
		# 기존 사진 URL 가져오기
		pilot = conn.execute('SELECT photo_url FROM pilots WHERE id = ?', (pilot_id,)).fetchone()
		photo_url = pilot['photo_url'] if pilot else '/static/images/default-pilot.jpg'
		
		# 파일 업로드 처리
		file = request.files.get('photo')
		if file and file.filename:
			filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_pilot_{callsign}_{file.filename}"
			filepath = os.path.join('static', 'members', filename)
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			file.save(filepath)
			photo_url = f'/static/members/{filename}'
		
		conn.execute('''
			UPDATE pilots 
			SET number = ?, position = ?, callsign = ?, generation = ?, aircraft = ?, 
			    photo_url = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP 
			WHERE id = ?
		''', (number_int, position, callsign, generation, aircraft, photo_url, order_num_int, is_active, pilot_id))
		conn.commit()
		conn.close()
		
		flash('조종사 정보가 수정되었습니다.', 'success')
		return redirect(url_for('admin_pilots'))
	
	pilot = conn.execute('SELECT * FROM pilots WHERE id = ?', (pilot_id,)).fetchone()
	conn.close()
	
	if not pilot:
		flash('조종사를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_pilots'))
	
	return render_template('admin/pilot_form.html', pilot=pilot)


# 조종사 삭제
@app.route('/admin/pilots/<int:pilot_id>/delete', methods=['POST'])
@login_required
def admin_pilot_delete(pilot_id):
	conn = get_db()
	conn.execute('DELETE FROM pilots WHERE id = ?', (pilot_id,))
	conn.commit()
	conn.close()
	
	flash('조종사가 삭제되었습니다.', 'success')
	return redirect(url_for('admin_pilots'))


# ========== 정비사 관리 ==========

# 정비사 목록
@app.route('/admin/maintenance')
@login_required
def admin_maintenance():
	conn = get_db()
	crew = conn.execute('SELECT * FROM maintenance_crew ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/maintenance.html', crew=crew)


# 정비사 추가
@app.route('/admin/maintenance/new', methods=['GET', 'POST'])
@login_required
def admin_maintenance_new():
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		role = request.form.get('role', '').strip()
		callsign = request.form.get('callsign', '').strip()
		bio = request.form.get('bio', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, callsign]):
			flash('이름과 콜사인은 필수 항목입니다.', 'error')
			return redirect(url_for('admin_maintenance_new'))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_maintenance_new'))
		
		# 사진 업로드 처리
		photo_url = '/static/images/default-crew.jpg'
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일 확장자 추출
				file_ext = os.path.splitext(file.filename)[1].lower()
				if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
					flash('이미지 파일만 업로드 가능합니다.', 'error')
					return redirect(url_for('admin_maintenance_new'))
				
				# 안전한 파일명 생성
				safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				filename = f'{timestamp}_crew_{safe_callsign}{file_ext}'
				
				# 파일 저장
				upload_folder = os.path.join(app.root_path, 'static', 'members')
				os.makedirs(upload_folder, exist_ok=True)
				file_path = os.path.join(upload_folder, filename)
				file.save(file_path)
				
				photo_url = f'/static/members/{filename}'
		
		# 데이터베이스에 저장
		conn = get_db()
		conn.execute('''
			INSERT INTO maintenance_crew (name, role, callsign, photo_url, bio, order_num, is_active)
			VALUES (?, ?, ?, ?, ?, ?, ?)
		''', (name, role, callsign, photo_url, bio, order_num_int, is_active))
		conn.commit()
		conn.close()
		
		flash('정비사가 추가되었습니다.', 'success')
		return redirect(url_for('admin_maintenance'))
	
	return render_template('admin/maintenance_form.html', crew=None)


# 정비사 수정
@app.route('/admin/maintenance/<int:crew_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_maintenance_edit(crew_id):
	conn = get_db()
	
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		role = request.form.get('role', '').strip()
		callsign = request.form.get('callsign', '').strip()
		bio = request.form.get('bio', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, callsign]):
			flash('이름과 콜사인은 필수 항목입니다.', 'error')
			return redirect(url_for('admin_maintenance_edit', crew_id=crew_id))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_maintenance_edit', crew_id=crew_id))
		
		# 현재 정비사 정보 가져오기
		current_crew = conn.execute('SELECT photo_url FROM maintenance_crew WHERE id = ?', (crew_id,)).fetchone()
		photo_url = current_crew['photo_url'] if current_crew else '/static/images/default-crew.jpg'
		
		# 사진 업로드 처리
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일 확장자 추출
				file_ext = os.path.splitext(file.filename)[1].lower()
				if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
					flash('이미지 파일만 업로드 가능합니다.', 'error')
					return redirect(url_for('admin_maintenance_edit', crew_id=crew_id))
				
				# 안전한 파일명 생성
				safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				filename = f'{timestamp}_crew_{safe_callsign}{file_ext}'
				
				# 파일 저장
				upload_folder = os.path.join(app.root_path, 'static', 'members')
				os.makedirs(upload_folder, exist_ok=True)
				file_path = os.path.join(upload_folder, filename)
				file.save(file_path)
				
				photo_url = f'/static/members/{filename}'
		
		# 데이터베이스 업데이트
		conn.execute('''
			UPDATE maintenance_crew
			SET name = ?, role = ?, callsign = ?, photo_url = ?, bio = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		''', (name, role, callsign, photo_url, bio, order_num_int, is_active, crew_id))
		conn.commit()
		conn.close()
		
		flash('정비사 정보가 수정되었습니다.', 'success')
		return redirect(url_for('admin_maintenance'))
	
	crew = conn.execute('SELECT * FROM maintenance_crew WHERE id = ?', (crew_id,)).fetchone()
	conn.close()
	
	if not crew:
		flash('정비사를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_maintenance'))
	
	return render_template('admin/maintenance_form.html', crew=crew)


# 정비사 삭제
@app.route('/admin/maintenance/<int:crew_id>/delete', methods=['POST'])
@login_required
def admin_maintenance_delete(crew_id):
	conn = get_db()
	conn.execute('DELETE FROM maintenance_crew WHERE id = ?', (crew_id,))
	conn.commit()
	conn.close()
	
	flash('정비사가 삭제되었습니다.', 'success')
	return redirect(url_for('admin_maintenance'))


# ========== 후보자 관리 ==========

# 후보자 목록
@app.route('/admin/candidates')
@login_required
def admin_candidates():
	conn = get_db()
	candidates = conn.execute('SELECT * FROM candidates ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/candidates.html', candidates=candidates)


# 후보자 추가
@app.route('/admin/candidates/new', methods=['GET', 'POST'])
@login_required
def admin_candidate_new():
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		callsign = request.form.get('callsign', '').strip()
		bio = request.form.get('bio', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, callsign]):
			flash('이름과 콜사인은 필수 항목입니다.', 'error')
			return redirect(url_for('admin_candidate_new'))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_candidate_new'))
		
		# 사진 업로드 처리
		photo_url = '/static/images/default-pilot.jpg'
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일 확장자 추출
				file_ext = os.path.splitext(file.filename)[1].lower()
				if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
					flash('이미지 파일만 업로드 가능합니다.', 'error')
					return redirect(url_for('admin_candidate_new'))
				
				# 안전한 파일명 생성
				safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				filename = f'{timestamp}_candidate_{safe_callsign}{file_ext}'
				
				# 파일 저장
				upload_folder = os.path.join(app.root_path, 'static', 'members')
				os.makedirs(upload_folder, exist_ok=True)
				file_path = os.path.join(upload_folder, filename)
				file.save(file_path)
				
				photo_url = f'/static/members/{filename}'
		
		# 데이터베이스에 저장
		conn = get_db()
		conn.execute('''
			INSERT INTO candidates (name, callsign, photo_url, bio, order_num, is_active)
			VALUES (?, ?, ?, ?, ?, ?)
		''', (name, callsign, photo_url, bio, order_num_int, is_active))
		conn.commit()
		conn.close()
		
		flash('후보자가 추가되었습니다.', 'success')
		return redirect(url_for('admin_candidates'))
	
	return render_template('admin/candidate_form.html', candidate=None)


# 후보자 수정
@app.route('/admin/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_candidate_edit(candidate_id):
	conn = get_db()
	
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		callsign = request.form.get('callsign', '').strip()
		bio = request.form.get('bio', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, callsign]):
			flash('이름과 콜사인은 필수 항목입니다.', 'error')
			return redirect(url_for('admin_candidate_edit', candidate_id=candidate_id))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_candidate_edit', candidate_id=candidate_id))
		
		# 현재 후보자 정보 가져오기
		current_candidate = conn.execute('SELECT photo_url FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
		photo_url = current_candidate['photo_url'] if current_candidate else '/static/images/default-pilot.jpg'
		
		# 사진 업로드 처리
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일 확장자 추출
				file_ext = os.path.splitext(file.filename)[1].lower()
				if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
					flash('이미지 파일만 업로드 가능합니다.', 'error')
					return redirect(url_for('admin_candidate_edit', candidate_id=candidate_id))
				
				# 안전한 파일명 생성
				safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				filename = f'{timestamp}_candidate_{safe_callsign}{file_ext}'
				
				# 파일 저장
				upload_folder = os.path.join(app.root_path, 'static', 'members')
				os.makedirs(upload_folder, exist_ok=True)
				file_path = os.path.join(upload_folder, filename)
				file.save(file_path)
				
				photo_url = f'/static/members/{filename}'
		
		# 데이터베이스 업데이트
		conn.execute('''
			UPDATE candidates
			SET name = ?, callsign = ?, photo_url = ?, bio = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		''', (name, callsign, photo_url, bio, order_num_int, is_active, candidate_id))
		conn.commit()
		conn.close()
		
		flash('후보자 정보가 수정되었습니다.', 'success')
		return redirect(url_for('admin_candidates'))
	
	candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
	conn.close()
	
	if not candidate:
		flash('후보자를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_candidates'))
	
	return render_template('admin/candidate_form.html', candidate=candidate)


# 후보자 삭제
@app.route('/admin/candidates/<int:candidate_id>/delete', methods=['POST'])
@login_required
def admin_candidate_delete(candidate_id):
	conn = get_db()
	conn.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
	conn.commit()
	conn.close()
	
	flash('후보자가 삭제되었습니다.', 'success')
	return redirect(url_for('admin_candidates'))


# ========== 전대장 인사말 관리 ==========
@app.route('/admin/commanders')
@login_required
def admin_commanders():
	conn = get_db()
	commanders = conn.execute('SELECT * FROM commander_greeting ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/commanders.html', commanders=commanders)


# 전대장 인사말 추가
@app.route('/admin/commanders/new', methods=['GET', 'POST'])
@login_required
def admin_commander_new():
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		rank = request.form.get('rank', '').strip()
		callsign = request.form.get('callsign', '').strip()
		generation = request.form.get('generation', '').strip()
		aircraft = request.form.get('aircraft', '').strip()
		greeting_text = request.form.get('greeting_text', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, rank, callsign, generation, aircraft]):
			flash('모든 필수 항목을 입력해주세요.', 'error')
			return redirect(url_for('admin_commander_new'))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_commander_new'))
		
		# 파일 업로드 처리
		photo_url = '/static/images/default-pilot.jpg'  # 기본 이미지
		file = request.files.get('photo')
		if file and file.filename:
			# 안전한 파일명 생성 (공백, 특수문자 제거)
			safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
			file_ext = os.path.splitext(file.filename)[1]  # 확장자 추출
			filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_commander_{safe_callsign}{file_ext}"
			filepath = os.path.join('static', 'members', filename)
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			file.save(filepath)
			photo_url = f'/static/members/{filename}'
		
		conn = get_db()
		conn.execute('''
			INSERT INTO commander_greeting (name, rank, callsign, generation, aircraft, photo_url, greeting_text, order_num, is_active)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		''', (name, rank, callsign, generation, aircraft, photo_url, greeting_text, order_num_int, is_active))
		conn.commit()
		conn.close()
		
		flash('전대장 인사말이 추가되었습니다.', 'success')
		return redirect(url_for('admin_commanders'))
	
	return render_template('admin/commander_form.html', commander=None)


# 전대장 인사말 수정
@app.route('/admin/commanders/<int:commander_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_commander_edit(commander_id):
	conn = get_db()
	
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		rank = request.form.get('rank', '').strip()
		callsign = request.form.get('callsign', '').strip()
		generation = request.form.get('generation', '').strip()
		aircraft = request.form.get('aircraft', '').strip()
		greeting_text = request.form.get('greeting_text', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([name, rank, callsign, generation, aircraft]):
			flash('모든 필수 항목을 입력해주세요.', 'error')
			return redirect(url_for('admin_commander_edit', commander_id=commander_id))
		
		try:
			order_num_int = int(order_num)
		except:
			flash('정렬 순서는 숫자여야 합니다.', 'error')
			return redirect(url_for('admin_commander_edit', commander_id=commander_id))
		
		# 기존 사진 URL 가져오기
		commander = conn.execute('SELECT photo_url FROM commander_greeting WHERE id = ?', (commander_id,)).fetchone()
		photo_url = commander['photo_url'] if commander else '/static/images/default-pilot.jpg'
		
		# 파일 업로드 처리
		file = request.files.get('photo')
		if file and file.filename:
			# 안전한 파일명 생성 (공백, 특수문자 제거)
			safe_callsign = ''.join(c for c in callsign if c.isalnum() or c in ('-', '_'))
			file_ext = os.path.splitext(file.filename)[1]  # 확장자 추출
			filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_commander_{safe_callsign}{file_ext}"
			filepath = os.path.join('static', 'members', filename)
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			file.save(filepath)
			photo_url = f'/static/members/{filename}'
		
		conn.execute('''
			UPDATE commander_greeting 
			SET name = ?, rank = ?, callsign = ?, generation = ?, aircraft = ?, 
			    photo_url = ?, greeting_text = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP 
			WHERE id = ?
		''', (name, rank, callsign, generation, aircraft, photo_url, greeting_text, order_num_int, is_active, commander_id))
		conn.commit()
		conn.close()
		
		flash('전대장 인사말이 수정되었습니다.', 'success')
		return redirect(url_for('admin_commanders'))
	
	commander = conn.execute('SELECT * FROM commander_greeting WHERE id = ?', (commander_id,)).fetchone()
	conn.close()
	
	if not commander:
		flash('전대장 인사말을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_commanders'))
	
	return render_template('admin/commander_form.html', commander=commander)


# 전대장 인사말 삭제
@app.route('/admin/commanders/<int:commander_id>/delete', methods=['POST'])
@login_required
def admin_commander_delete(commander_id):
	conn = get_db()
	conn.execute('DELETE FROM commander_greeting WHERE id = ?', (commander_id,))
	conn.commit()
	conn.close()
	
	flash('전대장 인사말이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_commanders'))


# 홈 콘텐츠 관리
@app.route('/admin/home-contents')
@login_required
def admin_home_contents():
	conn = get_db()
	contents = conn.execute('SELECT * FROM home_contents ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/home_contents.html', contents=contents)


# 홈 콘텐츠 추가
@app.route('/admin/home-contents/new', methods=['GET', 'POST'])
@login_required
def admin_home_content_new():
	if request.method == 'POST':
		content_type = request.form.get('content_type', '').strip()
		title = request.form.get('title', '').strip()
		content_data = request.form.get('content_data', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([content_type, content_data]):
			flash('콘텐츠 유형과 데이터를 입력해주세요.', 'error')
			return redirect(url_for('admin_home_content_new'))
		
		try:
			order_num_int = int(order_num)
		except:
			order_num_int = 0
		
		conn = get_db()
		conn.execute('''
			INSERT INTO home_contents (content_type, title, content_data, order_num, is_active)
			VALUES (?, ?, ?, ?, ?)
		''', (content_type, title, content_data, order_num_int, is_active))
		conn.commit()
		conn.close()
		
		flash('홈 콘텐츠가 추가되었습니다.', 'success')
		return redirect(url_for('admin_home_contents'))
	
	return render_template('admin/home_content_form.html', content=None)


# 홈 콘텐츠 수정
@app.route('/admin/home-contents/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_home_content_edit(content_id):
	conn = get_db()
	
	if request.method == 'POST':
		content_type = request.form.get('content_type', '').strip()
		title = request.form.get('title', '').strip()
		content_data = request.form.get('content_data', '').strip()
		order_num = request.form.get('order_num', '0').strip()
		is_active = 1 if request.form.get('is_active') else 0
		
		if not all([content_type, content_data]):
			flash('콘텐츠 유형과 데이터를 입력해주세요.', 'error')
			return redirect(url_for('admin_home_content_edit', content_id=content_id))
		
		try:
			order_num_int = int(order_num)
		except:
			order_num_int = 0
		
		conn.execute('''
			UPDATE home_contents 
			SET content_type = ?, title = ?, content_data = ?, order_num = ?, 
			    is_active = ?, updated_at = CURRENT_TIMESTAMP 
			WHERE id = ?
		''', (content_type, title, content_data, order_num_int, is_active, content_id))
		conn.commit()
		conn.close()
		
		flash('홈 콘텐츠가 수정되었습니다.', 'success')
		return redirect(url_for('admin_home_contents'))
	
	content = conn.execute('SELECT * FROM home_contents WHERE id = ?', (content_id,)).fetchone()
	conn.close()
	
	if not content:
		flash('콘텐츠를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_home_contents'))
	
	return render_template('admin/home_content_form.html', content=content)


# 홈 콘텐츠 삭제
@app.route('/admin/home-contents/<int:content_id>/delete', methods=['POST'])
@login_required
def admin_home_content_delete(content_id):
	conn = get_db()
	conn.execute('DELETE FROM home_contents WHERE id = ?', (content_id,))
	conn.commit()
	conn.close()
	
	flash('홈 콘텐츠가 삭제되었습니다.', 'success')
	return redirect(url_for('admin_home_contents'))


# ===== 팀소개 섹션 관리 =====
@app.route('/admin/about-sections')
@login_required
def admin_about_sections():
	conn = get_db()
	sections = conn.execute('SELECT * FROM about_sections ORDER BY order_num').fetchall()
	conn.close()
	return render_template('admin/about_sections.html', sections=sections)


@app.route('/admin/about-sections/new', methods=['GET', 'POST'])
@login_required
def admin_about_section_new():
	if request.method == 'POST':
		section_type = request.form.get('section_type', '').strip()
		title = request.form.get('title', '').strip()
		content = request.form.get('content', '').strip()
		order_num = int(request.form.get('order_num', 0))
		is_active = 1 if request.form.get('is_active') else 0
		
		if not section_type or not title:
			flash('섹션 유형과 제목은 필수입니다.', 'error')
			return redirect(url_for('admin_about_section_new'))
		
		# 사진 업로드 처리
		image_url = ''
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일명 생성 (타임스탬프_섹션타입)
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				safe_section = ''.join(c for c in section_type if c.isalnum() or c in ('-', '_'))
				file_ext = os.path.splitext(file.filename)[1].lower()
				filename = f"{timestamp}_section_{safe_section}{file_ext}"
				
				# 저장 경로
				upload_folder = os.path.join(app.static_folder, 'Picture')
				os.makedirs(upload_folder, exist_ok=True)
				filepath = os.path.join(upload_folder, filename)
				
				file.save(filepath)
				image_url = f'/static/Picture/{filename}'
		
		conn = get_db()
		conn.execute('''
			INSERT INTO about_sections (section_type, title, content, image_url, order_num, is_active, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
		''', (section_type, title, content, image_url, order_num, is_active))
		conn.commit()
		conn.close()
		
		flash('팀소개 섹션이 추가되었습니다.', 'success')
		return redirect(url_for('admin_about_sections'))
	
	return render_template('admin/about_section_form.html', section=None)


@app.route('/admin/about-sections/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_about_section_edit(section_id):
	conn = get_db()
	
	if request.method == 'POST':
		section_type = request.form.get('section_type', '').strip()
		title = request.form.get('title', '').strip()
		content = request.form.get('content', '').strip()
		order_num = int(request.form.get('order_num', 0))
		is_active = 1 if request.form.get('is_active') else 0
		
		if not section_type or not title:
			flash('섹션 유형과 제목은 필수입니다.', 'error')
			return redirect(url_for('admin_about_section_edit', section_id=section_id))
		
		# 기존 섹션 정보 가져오기
		section = conn.execute('SELECT * FROM about_sections WHERE id = ?', (section_id,)).fetchone()
		image_url = section['image_url'] if section else ''
		
		# 사진 업로드 처리
		if 'photo' in request.files:
			file = request.files['photo']
			if file and file.filename:
				# 파일명 생성 (타임스탬프_섹션타입)
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				safe_section = ''.join(c for c in section_type if c.isalnum() or c in ('-', '_'))
				file_ext = os.path.splitext(file.filename)[1].lower()
				filename = f"{timestamp}_section_{safe_section}{file_ext}"
				
				# 저장 경로
				upload_folder = os.path.join(app.static_folder, 'Picture')
				os.makedirs(upload_folder, exist_ok=True)
				filepath = os.path.join(upload_folder, filename)
				
				file.save(filepath)
				image_url = f'/static/Picture/{filename}'
		
		conn.execute('''
			UPDATE about_sections 
			SET section_type = ?, title = ?, content = ?, image_url = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		''', (section_type, title, content, image_url, order_num, is_active, section_id))
		conn.commit()
		conn.close()
		
		flash('팀소개 섹션이 수정되었습니다.', 'success')
		return redirect(url_for('admin_about_sections'))
	
	section = conn.execute('SELECT * FROM about_sections WHERE id = ?', (section_id,)).fetchone()
	conn.close()
	
	if not section:
		flash('섹션을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_about_sections'))
	
	return render_template('admin/about_section_form.html', section=section)


# 사진 게시판 관리 라우트
@app.route('/admin/gallery')
@login_required
def admin_gallery():
	conn = get_db()
	photos = conn.execute('SELECT * FROM gallery ORDER BY order_num, upload_date DESC').fetchall()
	conn.close()
	return render_template('admin/gallery.html', photos=photos)


@app.route('/admin/gallery/new', methods=['GET', 'POST'])
@login_required
def admin_gallery_new():
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		description = request.form.get('description', '').strip()
		image_url = request.form.get('image_url', '').strip()
		order_num = request.form.get('order_num', 0)
		is_active = 1 if request.form.get('is_active') else 0
		
		if not title or not image_url:
			flash('제목과 이미지 URL은 필수입니다.', 'error')
			return redirect(url_for('admin_gallery_new'))
		
		conn = get_db()
		conn.execute('''
			INSERT INTO gallery (title, description, image_url, order_num, is_active)
			VALUES (?, ?, ?, ?, ?)
		''', (title, description, image_url, order_num, is_active))
		conn.commit()
		conn.close()
		
		flash('사진이 추가되었습니다.', 'success')
		return redirect(url_for('admin_gallery'))
	
	return render_template('admin/gallery_form.html')


@app.route('/admin/gallery/edit/<int:photo_id>', methods=['GET', 'POST'])
@login_required
def admin_gallery_edit(photo_id):
	conn = get_db()
	
	if request.method == 'POST':
		title = request.form.get('title', '').strip()
		description = request.form.get('description', '').strip()
		image_url = request.form.get('image_url', '').strip()
		order_num = request.form.get('order_num', 0)
		is_active = 1 if request.form.get('is_active') else 0
		
		if not title or not image_url:
			flash('제목과 이미지 URL은 필수입니다.', 'error')
			return redirect(url_for('admin_gallery_edit', photo_id=photo_id))
		
		conn.execute('''
			UPDATE gallery 
			SET title = ?, description = ?, image_url = ?, order_num = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?
		''', (title, description, image_url, order_num, is_active, photo_id))
		conn.commit()
		conn.close()
		
		flash('사진이 수정되었습니다.', 'success')
		return redirect(url_for('admin_gallery'))
	
	photo = conn.execute('SELECT * FROM gallery WHERE id = ?', (photo_id,)).fetchone()
	conn.close()
	
	if not photo:
		flash('사진을 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_gallery'))
	
	return render_template('admin/gallery_form.html', photo=photo)


@app.route('/admin/gallery/delete/<int:photo_id>', methods=['POST'])
@login_required
def admin_gallery_delete(photo_id):
	conn = get_db()
	conn.execute('DELETE FROM gallery WHERE id = ?', (photo_id,))
	conn.commit()
	conn.close()
	
	flash('사진이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_gallery'))




@app.route('/admin/about-sections/<int:section_id>/delete', methods=['POST'])
@login_required
def admin_about_section_delete(section_id):
	conn = get_db()
	conn.execute('DELETE FROM about_sections WHERE id = ?', (section_id,))
	conn.commit()
	conn.close()
	
	flash('팀소개 섹션이 삭제되었습니다.', 'success')
	return redirect(url_for('admin_about_sections'))


# 사이트 이미지 관리 - 목록
@app.route('/admin/site-images')
@login_required
def admin_site_images():
	conn = get_db()
	images = conn.execute('SELECT * FROM site_images ORDER BY category, image_key').fetchall()
	conn.close()
	return render_template('admin/site_images.html', images=images)


# 사이트 이미지 수정
@app.route('/admin/site-images/<int:image_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_site_image_edit(image_id):
	conn = get_db()
	
	if request.method == 'POST':
		file = request.files.get('image')
		
		if file and file.filename:
			# 파일 저장
			filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
			filepath = os.path.join('static', 'images', filename)
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			file.save(filepath)
			
			image_path = f'/static/images/{filename}'
			
			# 데이터베이스 업데이트
			conn.execute('''
				UPDATE site_images 
				SET image_path = ?, updated_at = CURRENT_TIMESTAMP
				WHERE id = ?
			''', (image_path, image_id))
			conn.commit()
			
			flash('이미지가 업데이트되었습니다.', 'success')
		else:
			flash('이미지 파일을 선택해주세요.', 'error')
		
		conn.close()
		return redirect(url_for('admin_site_images'))
	
	image = conn.execute('SELECT * FROM site_images WHERE id = ?', (image_id,)).fetchone()
	conn.close()
	
	if not image:
		flash('이미지를 찾을 수 없습니다.', 'error')
		return redirect(url_for('admin_site_images'))
	
	return render_template('admin/site_image_form.html', image=image)


if __name__ == '__main__':
	# 데이터베이스 초기화
	init_db()
	
	# Allow selecting port via PORT env var (useful if 5000 is occupied).
	host = os.environ.get('HOST', '127.0.0.1')
	port = int(os.environ.get('PORT', 5001))
	# Run the dev server without the auto-reloader (single process) to avoid issues
	# when starting the app detached in this environment.
	app.run(host=host, port=port, debug=False, use_reloader=False)


