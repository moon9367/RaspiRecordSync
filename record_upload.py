import subprocess
import datetime
import os
import requests
import time

# 사용자 설정
upload_interval_seconds = 60  # 1분마다 저장 (테스트용)
video_duration_ms = 60000     # 60초 촬영 (rpicam-vid 기준)
nas_ip = "192.168.0.7"
nas_port = 8888
upload_path = "/cam/upload_raw.php"

def record_video(h264_file):
    print(f"▶ 촬영 시작: {h264_file}")
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
    # 현재 날짜시간을 가져와서 텍스트로 변환
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    convert_cmd = [
        "ffmpeg", "-fflags", "+genpts",
        "-r", "30", "-i", h264_file,
        "-vf", f"drawtext=text='{current_time}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", mp4_file
    ]
    result = subprocess.run(convert_cmd)
    return result.returncode == 0

def upload_to_nas(mp4_file):
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

def main():
    while True:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        h264_file = f"video_{timestamp}.h264"
        mp4_file = f"video_{timestamp}.mp4"

        if record_video(h264_file):
            if convert_to_mp4(h264_file, mp4_file):
                os.remove(h264_file)
                print(f"🧹 중간파일 삭제: {h264_file}")
                if upload_to_nas(mp4_file):
                    os.remove(mp4_file)
                    print("🧹 로컬 파일 삭제 완료")
                else:
                    print("⚠️ NAS 업로드 실패 - 파일 보존됨")
            else:
                print("❌ 변환 실패")
        else:
            print("❌ 촬영 실패")

        print(f"⏳ {upload_interval_seconds // 60}분 대기...\n")
        time.sleep(upload_interval_seconds)

if __name__ == "__main__":
    main()
