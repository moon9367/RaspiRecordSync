import subprocess
import datetime
import os
import requests
import time
import psutil
import threading
import queue

# 사용자 설정
upload_interval_seconds = 15  # 촬영 간격 (초) - 변환 시간 고려...
video_duration_ms = 10000     # 촬영 시간 (밀리초)
cam_number = 1  # CAM 번호 설정 (필요시 수정)
nas_ip = "tspol.iptime.org"
nas_port = 8888
upload_path = "/cam/upload.php"

# 전송 큐 및 상태 관리
upload_queue = queue.Queue()
upload_thread = None
stop_upload_thread = False

def get_cpu_info():
    """CPU 사용률과 온도 정보를 가져옵니다."""
    try:
        # CPU 사용률 가져오기 (interval=0으로 즉시 반환)
        cpu_percent = psutil.cpu_percent(interval=0)
        
        # CPU 온도 가져오기 (Raspberry Pi)
        temp_cmd = ["vcgencmd", "measure_temp"]
        temp_result = subprocess.run(temp_cmd, capture_output=True, text=True)
        if temp_result.returncode == 0:
            temp_str = temp_result.stdout.strip()
            temp_value = temp_str.replace("temp=", "").replace("'C", "")
            cpu_temp = float(temp_value)
        else:
            # 대체 방법으로 온도 확인
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

def record_video(h264_file):
    print(f"▶ 촬영 시작: {h264_file}")
    
    # 촬영 시작 전 정보 출력
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu_percent, cpu_temp = get_cpu_info()
    cam_info = f"CAM{cam_number} {current_time}"
    cpu_info = f"CPU: {cpu_percent:.1f}% | {cpu_temp:.1f}°C"
    print(f"📝 촬영 정보: {cam_info} | {cpu_info}")
    
    record_cmd = [
        "rpicam-vid",
        "-t", str(video_duration_ms),
        "-o", h264_file,
        "--width", "1920",
        "--height", "1080",
        "--framerate", "30",
        "--autofocus-mode", "auto",
        "--autofocus-speed", "normal",
        "--autofocus-range", "normal",
        "--vflip"  # 상하 반전
    ]
    result = subprocess.run(record_cmd)
    return result.returncode == 0

def convert_to_mp4(h264_file, mp4_file):
    print("🔄 mp4 변환 중...")
    
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
    result = subprocess.run(convert_cmd)
    
    # 임시 텍스트 파일 삭제
    try:
        os.remove(cam_text_file)
        os.remove(cpu_text_file)
    except:
        pass
    
    return result.returncode == 0

def upload_to_nas(mp4_file):
    """NAS로 파일을 업로드합니다."""
    print(f"🚀 NAS로 업로드 중: {mp4_file}")
    url = f"http://{nas_ip}:{nas_port}{upload_path}?filename={mp4_file}"
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
                
            print(f"📤 전송 큐에서 파일 가져옴: {mp4_file}")
            
            # 파일이 존재하는지 확인
            if os.path.exists(mp4_file):
                if upload_to_nas(mp4_file):
                    # 업로드 성공 시 로컬 파일 삭제
                    os.remove(mp4_file)
                    print(f"🧹 로컬 파일 삭제: {mp4_file}")
                else:
                    print(f"⚠️ 업로드 실패 - 파일 보존: {mp4_file}")
            else:
                print(f"❌ 파일이 존재하지 않음: {mp4_file}")
                
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

def process_video(h264_file, mp4_file):
    """비디오 변환 및 전송을 처리하는 함수"""
    try:
        print(f"🔄 백그라운드 변환 시작: {h264_file}")
        if convert_to_mp4(h264_file, mp4_file):
            os.remove(h264_file)
            print(f"🧹 중간파일 삭제: {h264_file}")
            
            # 전송 큐에 추가 (비동기 전송)
            upload_queue.put(mp4_file)
            print(f"📤 전송 큐에 추가: {mp4_file}")
            return True
        else:
            print("❌ 변환 실패")
            return False
    except Exception as e:
        print(f"❌ 비디오 처리 오류: {e}")
        return False

def main():
    print("🎬 RaspiRecordSync 시작")
    print(f"📹 CAM{cam_number} | 촬영 간격: {upload_interval_seconds}초 | 촬영 시간: {video_duration_ms//1000}초")
    
    # 전송 워커 스레드 시작
    start_upload_worker()
    
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            h264_file = f"video_{timestamp}.h264"
            mp4_file = f"video_{timestamp}.mp4"

            print(f"\n🎬 촬영 시작: {timestamp}")
            
            # 1. 촬영
            if record_video(h264_file):
                print("✅ 촬영 완료")
                
                # 2. 변환 및 전송을 별도 스레드에서 처리 (비동기)
                process_thread = threading.Thread(
                    target=process_video, 
                    args=(h264_file, mp4_file),
                    daemon=True
                )
                process_thread.start()
                print("🔄 백그라운드 처리 시작됨")
                
            else:
                print("❌ 촬영 실패")

            # 3. 다음 촬영까지 대기 (변환 완료를 기다리지 않음)
            print(f"⏳ {upload_interval_seconds}초 후 다음 촬영...")
            time.sleep(upload_interval_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 프로그램 종료 요청됨")
    except Exception as e:
        print(f"❌ 메인 루프 오류: {e}")
    finally:
        # 전송 워커 정리
        print("🧹 정리 중...")
        stop_upload_worker()
        print("👋 프로그램 종료")

if __name__ == "__main__":
    main()
