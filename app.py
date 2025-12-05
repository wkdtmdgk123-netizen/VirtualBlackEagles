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
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	''')
	
	# 기본 홈페이지 배너 설정
	cursor.execute('''
		INSERT OR IGNORE INTO banner_settings (page_name, background_image, title, subtitle, description, button_text, button_link)
		VALUES ('home', '/static/images/hero.jpg', 'Black Eagles', 'Republic Of Korea AirForce', 
		        '가상블랙이글스는 대한민국 블랙이글스의 다양한 특수비행을 통해 고도의 비행기량을 뽐내는 대한민국 가상 특수비행팀입니다.', 
		        'more', '#about')
	''')
	
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
		# 데이터베이스에 문의 내용 저장
		conn = get_db()
		cursor = conn.cursor()
		cursor.execute('''
			INSERT INTO contact_messages (name, email, message)
			VALUES (?, ?, ?)
		''', (name or '익명', email, message))
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
	conn.close()
	
	# 언어 설정을 템플릿에 전달
	if lang == 'en':
		return render_template('index_en.html', banner=banner, sections=sections)
	else:
		return render_template('index.html', banner=banner, sections=sections)


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
	conn.close()
	
	if lang == 'en':
		return render_template('about_en.html', banner=banner, sections=sections)
	else:
		return render_template('about.html', banner=banner, sections=sections)


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
	conn = get_db()
	messages = conn.execute('SELECT * FROM contact_messages ORDER BY created_at DESC').fetchall()
	conn.close()
	
	return render_template('admin/messages.html', messages=messages)


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
		
		if not title:
			flash('제목을 입력해주세요.', 'error')
			return redirect(url_for('admin_banner_edit', banner_id=banner_id))
		
		conn.execute('''
			UPDATE banner_settings 
			SET background_image = ?, title = ?, subtitle = ?, description = ?, 
			    button_text = ?, button_link = ?, title_font = ?, title_color = ?, 
			    subtitle_color = ?, description_color = ?, updated_at = CURRENT_TIMESTAMP 
			WHERE id = ?
		''', (background_image, title, subtitle, description, button_text, button_link,
		      title_font, title_color, subtitle_color, description_color, banner_id))
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


if __name__ == '__main__':
	# 데이터베이스 초기화
	init_db()
	
	# Allow selecting port via PORT env var (useful if 5000 is occupied).
	host = os.environ.get('HOST', '127.0.0.1')
	port = int(os.environ.get('PORT', 5001))
	# Run the dev server without the auto-reloader (single process) to avoid issues
	# when starting the app detached in this environment.
	app.run(host=host, port=port, debug=False, use_reloader=False)

