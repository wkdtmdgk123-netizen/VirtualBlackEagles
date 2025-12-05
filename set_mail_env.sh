#!/bin/bash
# 네이버 메일 설정 (실제 사용 전에 값을 입력하세요)

# 네이버 메일 주소와 앱 비밀번호를 입력하세요
export MAIL_SERVER="smtp.naver.com"
export MAIL_PORT="465"
export MAIL_USE_SSL="true"
export MAIL_USE_TLS="false"
export MAIL_USERNAME="rr3340@naver.com"
export MAIL_PASSWORD="YOUR_APP_PASSWORD_HERE"  # 네이버 앱 비밀번호로 변경하세요
export MAIL_DEFAULT_SENDER="rr3340@naver.com"

# Flask 앱 실행
cd /Users/jangseungha/Documents/블랙이글홈페이지
python3 app.py
