import subprocess
import datetime
import os
import time
import psutil
import threading
import signal
import sys

# 사용자 설정
upload_interval_seconds = 10  # 촬영 간격 (초)
video_duration_ms = 10000     # 촬영 시간 (밀리초)
cam_number = 1  # CAM 번호 설정 (필요시 수정)
output_dir = "recordings"     # 저장 디렉토리

# 전역 변수
current_cpu_percent = 0.0
current_cpu_temp = 0.0
stop_monitoring = False

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

def update_overlay_text():
    """오버레이 텍스트 파일을 실시간으로 업데이트"""
    global current_cpu_percent, current_cpu_temp, stop_monitoring
    
    while not stop_monitoring:
        try:
            # 현재 시간과 CPU 정보 가져오기
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cpu_percent, cpu_temp = get_cpu_info()
            
            # 전역 변수 업데이트
            current_cpu_percent = cpu_percent
            current_cpu_temp = cpu_temp
            
            # CAM 정보와 날짜시간 (좌측 상단)
            cam_time_text = f"CAM{cam_number} {current_time}"
            # CPU 정보 (우측 상단)
            cpu_text = f"CPU: {cpu_percent:.1f}%% | {cpu_temp:.1f}°C"
            
            # 오버레이 텍스트 파일 업데이트
            overlay_content = f"{cam_time_text}\n{cpu_text}"
            with open("realtime_overlay.txt", "w") as f:
                f.write(overlay_content)
            
            time.sleep(1)  # 1초마다 업데이트
        except Exception as e:
            print(f"오버레이 텍스트 업데이트 오류: {e}")
            time.sleep(1)

def record_video_with_realtime_overlay(h264_file):
    """실시간 오버레이와 함께 영상을 촬영합니다."""
    print(f"▶ 실시간 촬영 시작: {h264_file}")
    
    # 실시간 오버레이 필터 (텍스트 파일 사용)
    overlay_filter = (
        f"drawtext=textfile=realtime_overlay.txt:fontcolor=white:fontsize=24:"
        f"box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10:"
        f"reload=1"
    )
    
    # ffmpeg 명령어로 실시간 촬영
    record_cmd = [
        "ffmpeg",
        "-f", "v4l2",                    # Video4Linux2 입력
        "-video_size", "1920x1080",      # 해상도
        "-framerate", "30",              # 프레임레이트
        "-i", "/dev/video0",             # 카메라 장치
        "-t", str(video_duration_ms/1000),  # 촬영 시간 (초)
        "-vf", overlay_filter,           # 실시간 오버레이 필터
        "-c:v", "libx264",              # H.264 코덱
        "-preset", "ultrafast",          # 빠른 인코딩
        "-crf", "23",                   # 품질 설정
        "-y",                           # 파일 덮어쓰기
        h264_file
    ]
    
    print(f"📝 실시간 오버레이 활성화")
    
    result = subprocess.run(record_cmd, capture_output=True, text=True)
    return result.returncode == 0

def signal_handler(sig, frame):
    """시그널 핸들러"""
    global stop_monitoring
    print("\n🛑 종료 신호 수신")
    stop_monitoring = True
    sys.exit(0)

def main():
    global stop_monitoring
    
    print("🎬 RaspiRecordSync - 실시간 오버레이 촬영 v2")
    print(f"📹 CAM{cam_number} | 촬영 간격: {upload_interval_seconds}초 | 촬영 시간: {video_duration_ms//1000}초")
    print(f"📁 저장 위치: {output_dir}")
    print("🔄 실시간 CPU 모니터링 활성화")
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 저장 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 초기 오버레이 텍스트 파일 생성
    with open("realtime_overlay.txt", "w") as f:
        f.write("CAM1 초기화 중...\nCPU: 0.0%% | 0.0°C")
    
    # 실시간 오버레이 업데이트 스레드 시작
    overlay_thread = threading.Thread(target=update_overlay_text, daemon=True)
    overlay_thread.start()
    print("✅ 실시간 오버레이 업데이트 시작됨")
    
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            h264_file = os.path.join(output_dir, f"video_{timestamp}.h264")

            print(f"\n🎬 실시간 촬영 시작: {timestamp}")
            
            # 실시간 오버레이와 함께 촬영
            if record_video_with_realtime_overlay(h264_file):
                print("✅ 실시간 촬영 완료")
                print(f"💾 저장됨: {h264_file}")
            else:
                print("❌ 실시간 촬영 실패")

            print(f"⏳ {upload_interval_seconds}초 후 다음 촬영...")
            time.sleep(upload_interval_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 실시간 촬영 중지됨")
    except Exception as e:
        print(f"❌ 실시간 촬영 오류: {e}")
    finally:
        stop_monitoring = True
        # 임시 파일 정리
        try:
            os.remove("realtime_overlay.txt")
        except:
            pass
        print("👋 실시간 촬영 프로그램 종료")

if __name__ == "__main__":
    main() 