import subprocess
import datetime
import os
import time
import psutil
import requests
import threading
import queue
import glob

# 사용자 설정
input_dir = "recordings"      # 입력 디렉토리
nas_ip = "tspol.iptime.org"
nas_port = 8888
upload_path = "/cam/upload.php"
check_interval = 5  # 파일 체크 간격 (초)
log_file = "record_log.csv"

# 전송 큐 및 상태 관리
upload_queue = queue.Queue()
upload_thread = None
stop_upload_thread = False

# 파일이 완전히 저장(수정)된 후에만 처리
def is_file_stable(filepath, stable_seconds=2):
    if not os.path.exists(filepath):
        return False
    mtime = os.path.getmtime(filepath)
    return (time.time() - mtime) > stable_seconds

# 영상 변환: 워터마크 없이 단순 컨테이너 변환만
def convert_to_mp4(h264_file, mp4_file):
    print(f"🔄 변환 중: {os.path.basename(h264_file)}")
    convert_cmd = [
        "ffmpeg", "-fflags", "+genpts",
        "-r", "30", "-i", h264_file,
        "-c:v", "copy", mp4_file
    ]
    result = subprocess.run(convert_cmd, capture_output=True, text=True)
    return result.returncode == 0

def upload_to_nas(file_path):
    """NAS로 파일을 업로드합니다."""
    print(f"🚀 NAS로 업로드 중: {os.path.basename(file_path)}")
    url = f"http://{nas_ip}:{nas_port}{upload_path}?filename={os.path.basename(file_path)}"
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(url, data=f)
        if response.status_code == 200:
            print(f"✅ 업로드 완료: {os.path.basename(file_path)}")
            return True
        else:
            print(f"❌ 업로드 실패: {os.path.basename(file_path)} - 상태 코드: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 업로드 중 예외 발생: {e}")
        return False

def upload_worker():
    global stop_upload_thread
    print("📤 전송 워커 시작")
    while not stop_upload_thread:
        try:
            file_path = upload_queue.get(timeout=5)
            if file_path == "STOP":
                break
            print(f"📤 전송 큐에서 파일 가져옴: {os.path.basename(file_path)}")
            if os.path.exists(file_path):
                if upload_to_nas(file_path):
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
            time.sleep(1)
    print("📤 전송 워커 종료")

def start_upload_worker():
    global upload_thread
    if upload_thread is None or not upload_thread.is_alive():
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()
        print("📤 전송 워커 스레드 시작됨")

def stop_upload_worker():
    global stop_upload_thread, upload_thread
    stop_upload_thread = True
    upload_queue.put("STOP")
    if upload_thread and upload_thread.is_alive():
        upload_thread.join(timeout=5)
        print("📤 전송 워커 스레드 중지됨")

def process_video(h264_file):
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
    """10초마다 로그 파일을 NAS로 전송"""
    while not stop_upload_thread:
        if os.path.exists(log_file):
            upload_queue.put(log_file)
        time.sleep(10)

def main():
    print("📤 RaspiRecordSync - 전송 전용 (워터마크 없음, 로그 전송 포함)")
    print(f"입력 디렉토리: {input_dir}")
    print(f"NAS: {nas_ip}:{nas_port}")
    start_upload_worker()
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
        print("\n🛑 전송 중지됨")
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
    finally:
        print("🧹 정리 중...")
        stop_upload_worker()
        print("👋 전송 프로그램 종료")

if __name__ == "__main__":
    main() 