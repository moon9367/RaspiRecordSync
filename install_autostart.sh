#!/bin/bash

echo "🎬 RaspiRecordSync 자동 시작 설치"
echo "=================================="

# 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
echo "📁 현재 디렉토리: $CURRENT_DIR"

# systemd 서비스 파일 복사
echo "📦 systemd 서비스 파일 설치 중..."
sudo cp raspirecord.service /etc/systemd/system/

# 서비스 파일 경로 수정
echo "🔧 서비스 파일 경로 수정 중..."
sudo sed -i "s|/home/pi/RaspiRecordSync|$CURRENT_DIR|g" /etc/systemd/system/raspirecord.service

# systemd 재로드
echo "🔄 systemd 재로드 중..."
sudo systemctl daemon-reload

# 서비스 활성화
echo "✅ 서비스 활성화 중..."
sudo systemctl enable raspirecord.service

echo ""
echo "🎉 설치 완료!"
echo ""
echo "📋 사용 방법:"
echo "   시작: sudo systemctl start raspirecord"
echo "   중지: sudo systemctl stop raspirecord"
echo "   상태 확인: sudo systemctl status raspirecord"
echo "   로그 확인: sudo journalctl -u raspirecord -f"
echo ""
echo "🚀 다음 부팅부터 자동으로 시작됩니다!"
echo "🛑 지금 시작하려면: sudo systemctl start raspirecord" 