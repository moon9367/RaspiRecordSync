import subprocess
import datetime
import os
import requests
import time
import psutil

# 사용자 설정
upload_interval_seconds = 10  # 1분마다 저장 (테스트용)
video_duration_ms = 10000     # 60초 촬영 (rpicam-vid 기준)
cam_number = 1  # CAM 번호 설정 (필요시 수정)테스트
nas_ip = "tspol.iptime.org"
nas_port = 8888
upload_path = "/cam/upload.php"

def get_cpu_info():
    """CPU 사용률과 온도 정보를 가져옵니다."""
    try:
        # CPU 사용률 가져오기
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # CPU 온도 가져오기 (Raspberry Pi)
        temp_cmd = ["vcgencmd", "measure_temp"]
        temp_result = subprocess.run(temp_cmd, capture_output=True, text=True)
        if temp_result.returncode == 0:
            temp_str = temp_result.stdout.strip()
            temp_value = temp_str.replace("temp=", "").replace("'C", "")
            cpu_temp = float(temp_value)
        else:
            cpu_temp = 0.0
            
        return cpu_percent, cpu_temp
    except Exception as e:
        print(f"CPU 정보 가져오기 실패: {e}")
        return 0.0, 0.0

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
    
    # CAM 정보와 날짜시간 결합
    cam_time_info = f"CAM{cam_number} {current_time}"
    
    # CPU 정보 가져오기
    cpu_percent, cpu_temp = get_cpu_info()
    cpu_info = f"CPU: {cpu_percent:.1f}% | {cpu_temp:.1f}°C"
    
    # 복합 필터: CAM+날짜시간(좌측 상단) + CPU 정보(우측 상단)
    # 텍스트를 따옴표로 감싸서 처리
    filter_complex = (
        f"drawtext=text='{cam_time_info}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10,"
        f"drawtext=text='{cpu_info}':fontcolor=white:fontsize=16:box=1:boxcolor=black@0.5:boxborderw=3:x=w-tw-10:y=10"
    )
    
    convert_cmd = [
        "ffmpeg", "-fflags", "+genpts",
        "-r", "30", "-i", h264_file,
        "-vf", filter_complex,
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
