#!/bin/bash

echo "🔄 RaspiRecordSync 서비스 업데이트"
echo "=================================="

# 현재 디렉토리로 이동
cd ~/RaspiRecordSync

# 서비스 중지
echo "🛑 서비스 중지 중..."
sudo systemctl stop raspirecord

# 새 서비스 파일 복사
echo "📦 서비스 파일 업데이트 중..."
sudo cp raspirecord.service /etc/systemd/system/

# systemd 재로드
echo "🔄 systemd 재로드 중..."
sudo systemctl daemon-reload

# 서비스 재시작
echo "🚀 서비스 재시작 중..."
sudo systemctl start raspirecord

# 상태 확인
echo "📊 서비스 상태 확인..."
sudo systemctl status raspirecord

echo ""
echo "✅ 서비스 업데이트 완료!"
echo "📝 로그 확인: sudo journalctl -u raspirecord -f" 