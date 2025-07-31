#!/bin/bash

# SSH 키 설정 스크립트
# 이 스크립트는 SSH 키를 생성하고 원격 서버에 등록합니다.

echo "🔑 SSH 키 설정 시작"

# SSH 디렉토리 생성
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# SSH 키 생성 (이미 존재하면 건너뜀)
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "🔑 SSH 키 생성 중..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    echo "✅ SSH 키 생성 완료"
else
    echo "ℹ️ SSH 키가 이미 존재합니다."
fi

# SSH 키 권한 설정
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

echo "📋 공개 키 내용:"
cat ~/.ssh/id_rsa.pub

echo ""
echo "💡 다음 단계:"
echo "1. 위의 공개 키를 원격 서버의 ~/.ssh/authorized_keys 파일에 추가하세요"
echo "2. ssh_config.py 파일에서 SSH_KEY_PATH를 '/home/tspol/.ssh/id_rsa'로 설정하세요"
echo "3. 원격 서버에서 authorized_keys 파일 권한을 600으로 설정하세요"
echo ""
echo "원격 서버에서 실행할 명령어:"
echo "mkdir -p ~/.ssh"
echo "echo '위의 공개 키 내용' >> ~/.ssh/authorized_keys"
echo "chmod 600 ~/.ssh/authorized_keys"
echo "chmod 700 ~/.ssh" 