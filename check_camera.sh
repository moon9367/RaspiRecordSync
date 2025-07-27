#!/bin/bash

echo "📹 카메라 장치 확인"
echo "=================="

# 카메라 장치 확인
echo "🔍 카메라 장치 검색 중..."
ls -la /dev/video* 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 카메라 장치 발견"
else
    echo "❌ 카메라 장치를 찾을 수 없습니다"
fi

echo ""
echo "🔍 v4l2 장치 정보:"
v4l2-ctl --list-devices 2>/dev/null || echo "v4l2-ctl이 설치되지 않았습니다"

echo ""
echo "🔍 현재 사용자:"
whoami

echo ""
echo "🔍 video 그룹 확인:"
groups

echo ""
echo "🔍 /dev/video0 권한:"
ls -la /dev/video0 2>/dev/null || echo "/dev/video0가 존재하지 않습니다"

echo ""
echo "🔍 rpicam-vid 테스트:"
rpicam-vid --help | head -5 2>/dev/null || echo "rpicam-vid가 설치되지 않았습니다" 