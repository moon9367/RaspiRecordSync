# SSH 동기화 방식 업로드

PHP 방식에서 SSH를 통한 rsync 동기화 방식으로 변경된 업로드 시스템입니다.

## 주요 변경사항

- **PHP HTTP 업로드** → **SSH rsync 동기화**
- 더 안정적이고 빠른 파일 전송
- SSH 키 인증 지원
- 진행률 표시 및 오류 처리 개선

## 파일 구조

```
RaspiRecordSync/
├── upload_ssh_sync.py    # SSH 동기화 메인 스크립트
├── ssh_config.py         # SSH 연결 설정 파일
├── setup_ssh.sh          # SSH 키 설정 스크립트
├── upload.php            # 기존 PHP 업로드 (백업용)
└── upload_only.py        # 기존 HTTP 업로드 (백업용)
```

## 설정 방법

### 1. SSH 키 설정

```bash
# SSH 키 생성 및 설정
chmod +x setup_ssh.sh
./setup_ssh.sh
```

### 2. 원격 서버 설정

생성된 공개 키를 원격 서버에 등록:

```bash
# 원격 서버에서 실행
mkdir -p ~/.ssh
echo "생성된_공개_키_내용" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 3. 설정 파일 수정

`ssh_config.py` 파일을 수정하여 연결 정보를 설정:

```python
# 원격 서버 정보
REMOTE_HOST = "your-server.com"     # 원격 서버 호스트명
REMOTE_USER = "pi"                  # SSH 사용자명
REMOTE_PORT = 22                    # SSH 포트
REMOTE_PATH = "/home/pi/cam/"       # 원격 저장 경로

# SSH 키 설정
SSH_KEY_PATH = "/home/pi/.ssh/id_rsa"  # SSH 키 경로
```

## 사용법

### 기본 실행

```bash
python3 upload_ssh_sync.py
```

### 서비스로 등록

기존 서비스 파일을 SSH 방식으로 업데이트:

```bash
# 서비스 파일 수정
sudo nano /etc/systemd/system/raspirecord.service
```

서비스 파일에서 실행 명령어를 변경:
```ini
ExecStart=/usr/bin/python3 /home/pi/RaspiRecordSync/upload_ssh_sync.py
```

## 장점

1. **안정성**: SSH 연결은 HTTP보다 안정적
2. **속도**: rsync는 효율적인 파일 전송
3. **보안**: SSH 키 인증으로 보안 강화
4. **진행률**: 실시간 전송 진행률 표시
5. **재시작**: 네트워크 오류 시 자동 재시도

## 문제 해결

### SSH 연결 실패

1. SSH 키 설정 확인:
   ```bash
   ssh -i ~/.ssh/id_rsa pi@your-server.com
   ```

2. 원격 서버 SSH 서비스 확인:
   ```bash
   sudo systemctl status ssh
   ```

3. 방화벽 설정 확인:
   ```bash
   sudo ufw status
   ```

### rsync 명령어 수동 테스트

```bash
rsync -avz --progress -e "ssh -p 22 -i ~/.ssh/id_rsa" \
  test.mp4 pi@your-server.com:/home/pi/cam/
```

## 설정 옵션

`ssh_config.py`에서 추가 설정 가능:

- `SSH_CONNECT_TIMEOUT`: 연결 타임아웃 (초)
- `SSH_COMMAND_TIMEOUT`: 명령 실행 타임아웃 (초)
- `RSYNC_OPTIONS`: rsync 옵션 커스터마이징
- `DEBUG_MODE`: 디버그 로그 출력

## 기존 방식과의 비교

| 항목 | PHP HTTP 방식 | SSH rsync 방식 |
|------|---------------|----------------|
| 속도 | 보통 | 빠름 |
| 안정성 | 보통 | 높음 |
| 보안 | 기본 | 강화 |
| 설정 | 간단 | 복잡 |
| 오류 처리 | 기본 | 상세 |
| 진행률 | 없음 | 있음 | 