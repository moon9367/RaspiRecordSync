import requests
import datetime
import os
import time
import psutil
import threading
import queue
import glob
import urllib3
from discord_notify import DiscordNotifier

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 사용자 설정
input_dir = "/home/tspol/recordings"      # 입력 디렉토리
webdav_url = "http://tspol.iptime.org:5009"  # WebDAV URL (HTTP 사용)
webdav_user = "mms9989"                 # WebDAV 사용자명
webdav_password = "Wjswkwjs1!"         # WebDAV 패스워드
webdav_path = "/cam/"                   # WebDAV 경로 (간단한 경로)
check_interval = 5  # 파일 체크 간격 (초)
log_file = "/home/tspol/record_log.csv"

# 디스코드 웹훅 URL
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1398962742618095667/IVnyN4mNDHGHZxkJ_8b4N-IhIkM95kihJf25ZpXEEHqohY3GC9rOeB4BPyZVnUzXKv_T"

# 전송 큐 및 상태 관리
upload_queue = queue.Queue()
upload_thread = None
stop_upload_thread = False

def is_file_stable(filepath, stable_seconds=2):
    """파일이 완전히 저장(수정)된 후에만 처리"""
    if not os.path.exists(filepath):
        return False
    mtime = os.path.getmtime(filepath)
    return (time.time() - mtime) > stable_seconds

def convert_to_mp4(h264_file, mp4_file):
    """영상 변환: 워터마크 없이 단순 컨테이너 변환만"""
    print(f"🔄 변환 중: {os.path.basename(h264_file)}")
    convert_cmd = [
        "ffmpeg", "-fflags", "+genpts",
        "-r", "30", "-i", h264_file,
        "-c:v", "copy", mp4_file
    ]
    result = subprocess.run(convert_cmd, capture_output=True, text=True)
    return result.returncode == 0

def upload_via_webdav(file_path, discord_notifier=None):
    """WebDAV로 파일을 업로드합니다."""
    print(f"🚀 WebDAV로 업로드 중: {os.path.basename(file_path)}")
    
    # WebDAV URL 구성
    upload_url = f"{webdav_url}{webdav_path}{os.path.basename(file_path)}"
    
    try:
        # 파일 업로드
        with open(file_path, 'rb') as f:
            response = requests.put(
                upload_url,
                data=f,
                auth=(webdav_user, webdav_password),
                headers={'Content-Type': 'application/octet-stream'},
                timeout=300
            )
        
        if response.status_code in [200, 201, 204]:
            print(f"✅ WebDAV 업로드 완료: {os.path.basename(file_path)}")
            
            # 디스코드 알림 전송
            if discord_notifier:
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB 단위
                discord_notifier.send_webdav_upload_complete(
                    filename=os.path.basename(file_path),
                    file_size_mb=file_size,
                    server_host=webdav_url,
                    upload_time=datetime.datetime.now().strftime('%H:%M:%S')
                )
            
            return True
        else:
            print(f"❌ WebDAV 업로드 실패: {os.path.basename(file_path)} - 상태 코드: {response.status_code}")
            print(f"응답: {response.text}")
            
            # 디스코드 오류 알림
            if discord_notifier:
                discord_notifier.send_webdav_upload_error(
                    filename=os.path.basename(file_path),
                    error_message=f"상태 코드: {response.status_code}",
                    server_host=webdav_url
                )
            
            return False
            
    except Exception as e:
        print(f"❌ WebDAV 업로드 중 예외 발생: {e}")
        
        # 디스코드 오류 알림
        if discord_notifier:
            discord_notifier.send_webdav_upload_error(
                filename=os.path.basename(file_path),
                error_message=str(e),
                server_host=webdav_url
            )
        
        return False

def upload_worker(discord_notifier=None):
    """업로드 워커 스레드"""
    global stop_upload_thread
    print("📤 WebDAV 전송 워커 시작")
    
    while not stop_upload_thread:
        try:
            file_path = upload_queue.get(timeout=5)
            if file_path == "STOP":
                break
            print(f"📤 전송 큐에서 파일 가져옴: {os.path.basename(file_path)}")
            if os.path.exists(file_path):
                if upload_via_webdav(file_path, discord_notifier):
                    # 업로드 성공 시 로컬 파일 삭제(단, 로그 파일은 삭제하지 않음)
                    if not file_path.endswith('.csv'):
                        os.remove(file_path)
                        print(f"🧹 로컬 파일 삭제: {os.path.basename(file_path)}")
                else:
                    print(f"⚠️ 업로드 실패 - 파일 보존: {os.path.basename(file_path)}")
            else:
                print(f"❌ 파일이 존재하지 않음: {os.path.basename(file_path)}")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ 전송 워커 오류: {e}")
            if discord_notifier:
                discord_notifier.send_error_notification(f"전송 워커 오류: {e}")
            time.sleep(1)
    print("📤 WebDAV 전송 워커 종료")

def start_upload_worker(discord_notifier=None):
    """업로드 워커 스레드 시작"""
    global upload_thread
    if upload_thread is None or not upload_thread.is_alive():
        upload_thread = threading.Thread(target=upload_worker, args=(discord_notifier,), daemon=True)
        upload_thread.start()
        print("📤 WebDAV 전송 워커 스레드 시작됨")

def stop_upload_worker():
    """업로드 워커 스레드 중지"""
    global stop_upload_thread, upload_thread
    stop_upload_thread = True
    upload_queue.put("STOP")
    if upload_thread and upload_thread.is_alive():
        upload_thread.join(timeout=5)
        print("📤 WebDAV 전송 워커 스레드 중지됨")

def process_video(h264_file):
    """비디오 파일 처리"""
    try:
        mp4_file = h264_file.replace('.h264', '.mp4')
        if convert_to_mp4(h264_file, mp4_file):
            os.remove(h264_file)
            print(f"🧹 원본 파일 삭제: {os.path.basename(h264_file)}")
            upload_queue.put(mp4_file)
            print(f"📤 전송 큐에 추가: {os.path.basename(mp4_file)}")
            return True
        else:
            print("❌ 변환 실패")
            return False
    except Exception as e:
        print(f"❌ 비디오 처리 오류: {e}")
        return False

def upload_log_periodically():
    """60초마다 로그 파일을 WebDAV로 전송"""
    while not stop_upload_thread:
        if os.path.exists(log_file):
            upload_queue.put(log_file)
        time.sleep(60)

def test_webdav_connection():
    """WebDAV 연결 테스트"""
    print(f"🔍 WebDAV 연결 테스트 중: {webdav_url}")
    
    try:
        # 먼저 루트 경로로 테스트
        response = requests.get(
            webdav_url,
            auth=(webdav_user, webdav_password),
            timeout=10
        )
        print(f"📊 응답 상태 코드: {response.status_code}")
        print(f"📋 응답 헤더: {dict(response.headers)}")
        
        if response.status_code in [200, 207, 404]:
            print("✅ WebDAV 서버에 연결됨 (404는 정상일 수 있음)")
            return True
        else:
            print(f"❌ WebDAV 연결 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ WebDAV 연결 테스트 오류: {e}")
        return False

def main():
    print("📤 RaspiRecordSync - WebDAV 동기화 방식")
    print(f"입력 디렉토리: {input_dir}")
    print(f"WebDAV 서버: {webdav_url}")
    print(f"WebDAV 경로: {webdav_path}")
    
    # 디스코드 알림 초기화
    discord_notifier = None
    try:
        discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
        print("✅ 디스코드 알림 활성화됨")
    except Exception as e:
        print(f"⚠️ 디스코드 알림 초기화 실패: {e}")
    
    # WebDAV 연결 테스트
    if not test_webdav_connection():
        print("❌ WebDAV 연결에 실패했습니다. 설정을 확인해주세요.")
        print("💡 다음 사항들을 확인해주세요:")
        print("   1. webdav_url, webdav_user, webdav_password 설정")
        print("   2. NAS에서 WebDAV 서비스 활성화")
        print("   3. 방화벽 설정 (포트 5006)")
        return
    
    # WebDAV 시스템 시작 알림
    if discord_notifier:
        discord_notifier.send_webdav_system_start(webdav_url, webdav_user, webdav_path)
    
    start_upload_worker(discord_notifier)
    
    # 로그 파일 주기적 전송 스레드 시작
    log_thread = threading.Thread(target=upload_log_periodically, daemon=True)
    log_thread.start()
    
    processed_files = set()
    try:
        while True:
            h264_pattern = os.path.join(input_dir, "*.h264")
            h264_files = glob.glob(h264_pattern)
            for h264_file in h264_files:
                if h264_file not in processed_files and is_file_stable(h264_file, 2):
                    print(f"\n📁 새 파일 발견: {os.path.basename(h264_file)}")
                    processed_files.add(h264_file)
                    process_thread = threading.Thread(
                        target=process_video, 
                        args=(h264_file,),
                        daemon=True
                    )
                    process_thread.start()
                    print("🔄 백그라운드 처리 시작됨")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("\n🛑 WebDAV 전송 중지됨")
    except Exception as e:
        print(f"❌ WebDAV 전송 오류: {e}")
    finally:
        print("🧹 정리 중...")
        stop_upload_worker()
        print("👋 WebDAV 전송 프로그램 종료")

if __name__ == "__main__":
    main() 