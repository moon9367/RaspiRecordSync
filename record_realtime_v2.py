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
stop_monitoring = False

def get_cpu_info():
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

def update_cpu_overlay_text():
    global stop_monitoring
    while not stop_monitoring:
        try:
            cpu_percent, cpu_temp = get_cpu_info()
            cpu_text = f"CPU: {cpu_percent:.1f}% | {cpu_temp:.1f}°C"
            with open("cpu_overlay.txt", "w") as f:
                f.write(cpu_text)
            time.sleep(1)
        except Exception as e:
            print(f"오버레이 텍스트 업데이트 오류: {e}")
            time.sleep(1)

def record_video_with_overlay(output_file):
    print(f"▶ 실시간 촬영 시작: {output_file}")
    temp_h264 = output_file.replace('.h264', '_temp.h264')
    try:
        # 1단계: rpicam-vid로 촬영
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
            "--vflip"
        ]
        record_result = subprocess.run(record_cmd, capture_output=True, text=True)
        if record_result.returncode != 0:
            print("❌ 촬영 실패")
            return False
        # 2단계: 변환 시점의 날짜/시간, CPU 정보로 오버레이 추가
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu_percent, cpu_temp = get_cpu_info()
        cam_time_text = f"CAM{cam_number} {now}"
        cpu_text = f"CPU: {cpu_percent:.1f}% | {cpu_temp:.1f}°C"
        overlay_filter = (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{cam_time_text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{cpu_text}':fontcolor=white:fontsize=16:box=1:boxcolor=black@0.5:boxborderw=3:x=w-tw-10:y=10"
        )
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
        try:
            os.remove(temp_h264)
        except:
            pass
        if overlay_result.returncode != 0:
            print("❌ 오버레이 추가 실패")
            return False
        print("✅ 오버레이 촬영 완료")
        return True
    except Exception as e:
        print(f"❌ 촬영 오류: {e}")
        try:
            os.remove(temp_h264)
        except:
            pass
        return False

def signal_handler(sig, frame):
    global stop_monitoring
    print("\n🛑 종료 신호 수신")
    stop_monitoring = True
    sys.exit(0)

def main():
    global stop_monitoring
    print("🎬 RaspiRecordSync - 오버레이 촬영 (변환 시점 정보)")
    print(f"📹 CAM{cam_number} | 촬영 시간: {video_duration_ms//1000}초씩 연속 저장")
    print(f"📁 저장 위치: {output_dir}")
    print("🔄 실시간 CPU 모니터링 활성화")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    os.makedirs(output_dir, exist_ok=True)
    # CPU 오버레이 텍스트 스레드 시작
    cpu_thread = threading.Thread(target=update_cpu_overlay_text, daemon=True)
    cpu_thread.start()
    print("✅ CPU 오버레이 텍스트 스레드 시작됨")
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            h264_file = os.path.join(output_dir, f"video_{timestamp}.h264")
            print(f"\n🎬 실시간 촬영 시작: {timestamp}")
            if record_video_with_overlay(h264_file):
                print("✅ 오버레이 촬영 완료")
                print(f"💾 저장됨: {h264_file}")
            else:
                print("❌ 실시간 촬영 실패")
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