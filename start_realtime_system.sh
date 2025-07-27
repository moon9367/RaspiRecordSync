#!/bin/bash

echo "🎬 RaspiRecordSync 실시간 오버레이 시스템 시작"
echo "================================================"

# 필요한 패키지 설치 확인
echo "📦 패키지 확인 중..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg가 설치되지 않았습니다."
    exit 1
fi

# 카메라 장치 확인 (rpicam-vid 사용하므로 제거)
echo "📹 Raspberry Pi Camera 사용"

# Python 패키지 확인
echo "🐍 Python 패키지 확인 중..."
python3 -c "import psutil, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 필요한 Python 패키지 설치 중..."
    pip install psutil requests
fi

# recordings 디렉토리 생성
mkdir -p recordings

echo "✅ 시스템 준비 완료"
echo ""

# 실시간 촬영 스크립트 자동 선택
RECORD_SCRIPT="record_realtime_v2.py"
echo "✅ 안정적인 실시간 오버레이 사용"

echo ""
echo "🎬 실시간 오버레이 촬영 시스템 시작..."
echo "📹 촬영 스크립트: $RECORD_SCRIPT"
echo "📤 전송 스크립트: upload_only.py"
echo ""

# 백그라운드에서 전송 스크립트 시작
echo "📤 전송 시스템 시작..."
python3 upload_only.py &
UPLOAD_PID=$!

# 잠시 대기
sleep 2

# 실시간 촬영 스크립트 시작
echo "🎬 실시간 촬영 시스템 시작..."
python3 $RECORD_SCRIPT &
RECORD_PID=$!

echo ""
echo "🎯 실시간 오버레이 시스템이 실행 중입니다."
echo "📹 촬영 PID: $RECORD_PID"
echo "📤 전송 PID: $UPLOAD_PID"
echo ""
echo "🔄 실시간 CPU 모니터링 및 오버레이 활성화됨"
echo "🛑 중지하려면 Ctrl+C를 누르세요."

# 종료 처리
trap 'echo ""; echo "🛑 시스템 종료 중..."; kill $RECORD_PID $UPLOAD_PID 2>/dev/null; wait; echo "👋 시스템 종료됨"; exit 0' INT TERM

# 프로세스 모니터링
while true; do
    if ! kill -0 $RECORD_PID 2>/dev/null; then
        echo "❌ 실시간 촬영 프로세스가 종료되었습니다."
        break
    fi
    
    if ! kill -0 $UPLOAD_PID 2>/dev/null; then
        echo "❌ 전송 프로세스가 종료되었습니다."
        break
    fi
    
    sleep 5
done

# 정리
kill $RECORD_PID $UPLOAD_PID 2>/dev/null
wait
echo "👋 실시간 오버레이 시스템 종료됨" 