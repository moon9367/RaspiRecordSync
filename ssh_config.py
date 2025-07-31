# SSH 연결 설정
# 이 파일을 수정하여 SSH 연결 정보를 설정하세요

# 원격 서버 정보
REMOTE_HOST = "tspol.iptime.org"  # 원격 서버 호스트명 또는 IP
REMOTE_USER = "tspol9983"          # SSH 사용자명 (실제 NAS 사용자명으로 수정)
REMOTE_PORT = 22                   # SSH 포트 (기본값: 22)
REMOTE_PATH = "/volume1/cam/"      # 원격 서버의 저장 경로 (NAS volume1)

# SSH 키 설정 (선택사항)
# SSH 키를 사용하지 않으면 None으로 설정
SSH_KEY_PATH = "/home/tspol/.ssh/id_rsa"  # tspol 사용자 경로로 수정

# SSH 연결 타임아웃 설정
SSH_CONNECT_TIMEOUT = 10  # 연결 타임아웃 (초)
SSH_COMMAND_TIMEOUT = 300 # 명령 실행 타임아웃 (초)

# rsync 옵션
RSYNC_OPTIONS = [
    "-avz",           # 아카이브 모드, 상세 출력, 압축
    "--progress",     # 진행률 표시
    "--partial",      # 부분 전송 지원 (대용량 파일용)
    "--timeout=300"   # rsync 타임아웃
]

# 디버그 모드 (True로 설정하면 상세한 로그 출력)
DEBUG_MODE = False 