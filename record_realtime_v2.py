import subprocess
import datetime
import os
import time
import psutil
import signal
import sys
import csv

# 사용자 설정
video_duration_ms = 10000     # 촬영 시간 (밀리초) - 10초씩 끊어서 저장
output_dir = "recordings"     # 저장 디렉토리
log_file = "record_log.csv"   # 로그 파일명11

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

def record_video(output_file):
    print(f"▶ 촬영 시작: {output_file}")
    try:
        record_cmd = [
            "rpicam-vid",
            "-t", str(video_duration_ms),
            "--codec", "h264",
            "--output", output_file,
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
        print("✅ 촬영 완료")
        return True
    except Exception as e:
        print(f"❌ 촬영 오류: {e}")
        return False

def log_to_csv(filename, timestamp, cpu_percent, cpu_temp):
    header = ["filename", "timestamp", "cpu_percent", "cpu_temp"]
    file_exists = os.path.isfile(log_file)
    with open(log_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(header)
        writer.writerow([filename, timestamp, f"{cpu_percent:.1f}", f"{cpu_temp:.1f}"])

def signal_handler(sig, frame):
    print("\n🛑 종료 신호 수신")
    sys.exit(0)

def main():
    print("🎬 RaspiRecordSync - 영상 저장 및 CSV 로그 기록")
    print(f"촬영 시간: {video_duration_ms//1000}초씩 연속 저장")
    print(f"📁 저장 위치: {output_dir}")
    print(f"📝 로그 파일: {log_file}")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    os.makedirs(output_dir, exist_ok=True)
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            h264_file = os.path.join(output_dir, f"video_{timestamp}.h264")
            print(f"\n🎬 촬영 시작: {timestamp}")
            cpu_percent, cpu_temp = get_cpu_info()
            if record_video(h264_file):
                print(f"💾 저장됨: {h264_file}")
                log_to_csv(h264_file, timestamp, cpu_percent, cpu_temp)
                print(f"📝 로그 기록 완료: {h264_file}, {timestamp}, {cpu_percent:.1f}, {cpu_temp:.1f}")
            else:
                print("❌ 촬영 실패")
            print("🔄 연속 촬영 진행...")
    except KeyboardInterrupt:
        print("\n🛑 실시간 촬영 중지됨")
    except Exception as e:
        print(f"❌ 실시간 촬영 오류: {e}")
    finally:
        print("👋 실시간 촬영 프로그램 종료")

if __name__ == "__main__":
    main() 