import subprocess
import datetime
import os
import time
import psutil
import threading
import signal
import sys

# 사용자 설정
video_duration_ms = 10000     # 촬영 시간 (밀리초) - 10초씩 끊어서 저장
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

def record_video_with_realtime_overlay(output_file):
    """실시간 오버레이와 함께 영상을 촬영합니다."""
    print(f"▶ 실시간 촬영 시작: {output_file}")
    
    # 임시 H.264 파일명
    temp_h264 = output_file.replace('.h264', '_temp.h264')
    
    try:
        # 1단계: rpicam-vid로 촬영
        print("📹 1단계: 카메라 촬영")
        record_cmd = [
            "rpicam-vid",
            "-t", str(video_duration_ms),
            "--codec", "h264",
            "--output", temp_h264,
            "--width", "1920",
            "--height", "1080",
            "--framerate", "30",
            "--autofocus-mode", "auto",
            "--autofocus-speed", "normal",
            "--autofocus-range", "normal",
            "--vflip"  # 상하 반전
        ]
        
        record_result = subprocess.run(record_cmd, capture_output=True, text=True)
        
        if record_result.returncode != 0:
            print("❌ 촬영 실패")
            return False
        
        # 2단계: 실시간 CPU 정보로 오버레이 추가
        print("🎨 2단계: 실시간 오버레이 추가")
        
        # 현재 시간과 CPU 정보 가져오기 (촬영 완료 시점)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu_percent, cpu_temp = get_cpu_info()
        
        # CAM 정보와 날짜시간 (좌측 상단)
        cam_time_text = f"CAM{cam_number} {current_time}"
        # CPU 정보 (우측 상단)
        cpu_text = f"CPU: {cpu_percent:.1f}%% | {cpu_temp:.1f}°C"
        
        # 실시간 오버레이 필터
        overlay_filter = (
            f"drawtext=text='{cam_time_text}':fontcolor=white:fontsize=24:"
            f"box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10,"
            f"drawtext=text='{cpu_text}':fontcolor=white:fontsize=16:"
            f"box=1:boxcolor=black@0.5:boxborderw=3:x=w-tw-10:y=10"
        )
        
        print(f"📝 실시간 오버레이: {cam_time_text} | {cpu_text}")
        
        # ffmpeg로 오버레이 추가
        overlay_cmd = [
            "ffmpeg",
            "-i", temp_h264,
            "-vf", overlay_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast", 
            "-crf", "23",
            "-y",
            output_file
        ]
        
        overlay_result = subprocess.run(overlay_cmd, capture_output=True, text=True)
        
        # 임시 파일 삭제
        try:
            os.remove(temp_h264)
        except:
            pass
        
        if overlay_result.returncode != 0:
            print("❌ 오버레이 추가 실패")
            return False
            
        print("✅ 실시간 오버레이 촬영 완료")
        return True
        
    except Exception as e:
        print(f"❌ 촬영 오류: {e}")
        
        # 임시 파일 정리
        try:
            os.remove(temp_h264)
        except:
            pass
            
        return False

def signal_handler(sig, frame):
    """시그널 핸들러"""
    global stop_monitoring
    print("\n🛑 종료 신호 수신")
    stop_monitoring = True
    sys.exit(0)

def main():
    global stop_monitoring
    
    print("🎬 RaspiRecordSync - 실시간 오버레이 촬영 v2")
    print(f"📹 CAM{cam_number} | 촬영 시간: {video_duration_ms//1000}초씩 연속 저장")
    print(f"📁 저장 위치: {output_dir}")
    print("🔄 실시간 CPU 모니터링 활성화")
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 저장 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # CPU 모니터링 스레드 시작
    cpu_thread = threading.Thread(target=update_overlay_text, daemon=True)
    cpu_thread.start()
    print("✅ CPU 모니터링 시작됨")
    
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

            # 연속 촬영 - 대기 없이 바로 다음 촬영
            print("🔄 연속 촬영 진행...")
            
    except KeyboardInterrupt:
        print("\n🛑 실시간 촬영 중지됨")
    except Exception as e:
        print(f"❌ 실시간 촬영 오류: {e}")
    finally:
        stop_monitoring = True
        print("👋 실시간 촬영 프로그램 종료")

if __name__ == "__main__":
    main() 