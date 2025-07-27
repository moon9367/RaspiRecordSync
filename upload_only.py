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
cam_number = 1  # CAM 번호 설정 (필요시 수정)
input_dir = "recordings"      # 입력 디렉토리
nas_ip = "tspol.iptime.org"
nas_port = 8888
upload_path = "/cam/upload.php"
check_interval = 5  # 파일 체크 간격 (초)

# 전송 큐 및 상태 관리
upload_queue = queue.Queue()
upload_thread = None
stop_upload_thread = False

def get_cpu_info():
    """CPU 사용률과 온도 정보를 가져옵니다."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0)
        
        temp_cmd = ["vcgencmd", "measure_temp"]
        temp_result = subprocess.run(temp_cmd, capture_output=True, text=True)
        if temp_result.returncode == 0:
            temp_str = temp_result.stdout.strip()
            temp_value = temp_str.replace("temp=", "").replace("'C", "")
            cpu_temp = float(temp_value)
        else:
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    cpu_temp = float(temp_raw) / 1000.0
            except:
                cpu_temp = 0.0
            
        return cpu_percent, cpu_temp
    except Exception as e:
        print(f"CPU 정보 가져오기 실패: {e}")
        return 0.0, 0.0

def convert_to_mp4(h264_file, mp4_file):
    """H.264 파일을 MP4로 변환하면서 오버레이를 추가합니다."""
    print(f"🔄 변환 중: {os.path.basename(h264_file)}")
    
    # 현재 날짜시간과 CPU 정보 가져오기
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu_percent, cpu_temp = get_cpu_info()
    
    # CAM 정보와 날짜시간 (좌측 상단)
    cam_time_info = f"CAM{cam_number} {current_time}"
    # CPU 정보 (우측 상단) - % 문자를 이스케이프 처리
    cpu_info = f"CPU: {cpu_percent:.1f}%% | {cpu_temp:.1f}°C"
    
    # 텍스트 파일 생성
    cam_text_file = "cam_text.txt"
    cpu_text_file = "cpu_text.txt"
    
    with open(cam_text_file, 'w') as f:
        f.write(cam_time_info)
    with open(cpu_text_file, 'w') as f:
        f.write(cpu_info)
    
    # 복합 필터: CAM+날짜시간(좌측 상단) + CPU 정보(우측 상단)
    filter_complex = (
        f"drawtext=textfile={cam_text_file}:fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10,"
        f"drawtext=textfile={cpu_text_file}:fontcolor=white:fontsize=16:box=1:boxcolor=black@0.5:boxborderw=3:x=w-tw-10:y=10"
    )
    
    convert_cmd = [
        "ffmpeg", "-fflags", "+genpts",
        "-r", "30", "-i", h264_file,
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", mp4_file
    ]
    result = subprocess.run(convert_cmd, capture_output=True, text=True)
    
    # 임시 텍스트 파일 삭제
    try:
        os.remove(cam_text_file)
        os.remove(cpu_text_file)
    except:
        pass
    
    return result.returncode == 0

def upload_to_nas(mp4_file):
    """NAS로 파일을 업로드합니다."""
    print(f"🚀 NAS로 업로드 중: {os.path.basename(mp4_file)}")
    url = f"http://{nas_ip}:{nas_port}{upload_path}?filename={os.path.basename(mp4_file)}"
    try:
        with open(mp4_file, 'rb') as f:
            response = requests.post(url, data=f)
        if response.status_code == 200:
            print("✅ 업로드 완료")
            return True
        else:
            print(f"⚠️ 업로드 실패 - 상태 코드: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 업로드 중 예외 발생: {e}")
        return False

def upload_worker():
    """전송 작업을 처리하는 워커 스레드"""
    global stop_upload_thread
    print("📤 전송 워커 시작")
    
    while not stop_upload_thread:
        try:
            # 큐에서 파일 경로 가져오기 (5초 타임아웃)
            mp4_file = upload_queue.get(timeout=5)
            
            if mp4_file == "STOP":
                break
                
            print(f"📤 전송 큐에서 파일 가져옴: {os.path.basename(mp4_file)}")
            
            # 파일이 존재하는지 확인
            if os.path.exists(mp4_file):
                if upload_to_nas(mp4_file):
                    # 업로드 성공 시 로컬 파일 삭제
                    os.remove(mp4_file)
                    print(f"🧹 로컬 파일 삭제: {os.path.basename(mp4_file)}")
                else:
                    print(f"⚠️ 업로드 실패 - 파일 보존: {os.path.basename(mp4_file)}")
            else:
                print(f"❌ 파일이 존재하지 않음: {os.path.basename(mp4_file)}")
                
        except queue.Empty:
            # 타임아웃 - 계속 대기
            continue
        except Exception as e:
            print(f"❌ 전송 워커 오류: {e}")
            time.sleep(1)
    
    print("📤 전송 워커 종료")

def start_upload_worker():
    """전송 워커 스레드를 시작합니다."""
    global upload_thread
    if upload_thread is None or not upload_thread.is_alive():
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()
        print("📤 전송 워커 스레드 시작됨")

def stop_upload_worker():
    """전송 워커 스레드를 중지합니다."""
    global stop_upload_thread, upload_thread
    stop_upload_thread = True
    upload_queue.put("STOP")
    if upload_thread and upload_thread.is_alive():
        upload_thread.join(timeout=5)
        print("📤 전송 워커 스레드 중지됨")

def process_video(h264_file):
    """비디오 변환 및 전송을 처리하는 함수"""
    try:
        # MP4 파일명 생성
        mp4_file = h264_file.replace('.h264', '.mp4')
        
        # 변환
        if convert_to_mp4(h264_file, mp4_file):
            # 원본 H.264 파일 삭제
            os.remove(h264_file)
            print(f"🧹 원본 파일 삭제: {os.path.basename(h264_file)}")
            
            # 전송 큐에 추가
            upload_queue.put(mp4_file)
            print(f"📤 전송 큐에 추가: {os.path.basename(mp4_file)}")
            return True
        else:
            print("❌ 변환 실패")
            return False
    except Exception as e:
        print(f"❌ 비디오 처리 오류: {e}")
        return False

def main():
    print("📤 RaspiRecordSync - 전송 전용")
    print(f"📹 CAM{cam_number} | 입력 디렉토리: {input_dir}")
    print(f"🌐 NAS: {nas_ip}:{nas_port}")
    
    # 전송 워커 스레드 시작
    start_upload_worker()
    
    # 처리된 파일 목록
    processed_files = set()
    
    try:
        while True:
            # H.264 파일 검색
            h264_pattern = os.path.join(input_dir, "*.h264")
            h264_files = glob.glob(h264_pattern)
            
            # 새로운 파일 처리
            for h264_file in h264_files:
                if h264_file not in processed_files:
                    print(f"\n📁 새 파일 발견: {os.path.basename(h264_file)}")
                    processed_files.add(h264_file)
                    
                    # 변환 및 전송을 별도 스레드에서 처리
                    process_thread = threading.Thread(
                        target=process_video, 
                        args=(h264_file,),
                        daemon=True
                    )
                    process_thread.start()
                    print("🔄 백그라운드 처리 시작됨")
            
            # 잠시 대기
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 전송 중지됨")
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
    finally:
        # 전송 워커 정리
        print("🧹 정리 중...")
        stop_upload_worker()
        print("👋 전송 프로그램 종료")

if __name__ == "__main__":
    main() 