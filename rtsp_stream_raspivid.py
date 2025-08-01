#!/usr/bin/env python3
"""
라즈베리파이 모듈3 카메라용 RTSP 스트리밍 스크립트
raspivid를 사용하여 직접 RTSP 스트리밍
"""

import subprocess
import time
import signal
import sys
import socket
from discord_notify import DiscordNotifier

# RTSP 설정
RTSP_PORT = 8554
RTSP_PATH = "live"

# 디스코드 웹훅 URL
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1398962742618095667/IVnyN4mNDHGHZxkJ_8b4N-IhIkM95kihJf25ZpXEEHqohY3GC9rOeB4BPyZVnUzXKv_T"

def get_raspberry_pi_ip():
    """라즈베리파이 IP 주소 가져오기"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "라즈베리파이IP"

def check_camera():
    """카메라 상태 확인"""
    try:
        result = subprocess.run(["vcgencmd", "get_camera"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"📹 카메라 상태: {result.stdout.strip()}")
            return True
        else:
            print("❌ 카메라 상태 확인 실패")
            return False
    except Exception as e:
        print(f"❌ 카메라 확인 오류: {e}")
        return False

def start_rtsp_stream():
    """RTSP 스트림 시작"""
    try:
        print("🎥 RTSP 스트림 시작 중...")
        
        # 카메라 상태 확인
        if not check_camera():
            print("⚠️ 카메라가 활성화되지 않았습니다.")
            print("💡 해결 방법:")
            print("   1. sudo raspi-config 실행")
            print("   2. Interface Options → Camera → Enable")
            print("   3. 라즈베리파이 재부팅")
            return False
        
        # raspivid + ffmpeg 파이프라인
        raspivid_cmd = [
            "raspivid",
            "-t", "0",                     # 무한 실행
            "-w", "1280",                  # 너비
            "-h", "720",                   # 높이
            "-fps", "25",                  # 프레임레이트
            "-b", "2500000",               # 비트레이트 (2.5Mbps)
            "-o", "-",                     # stdout으로 출력
            "-n",                          # 미리보기 비활성화
            "-g", "25",                    # GOP 크기
            "-pf", "baseline",             # 프로파일
            "-lev", "3.1"                 # 레벨
        ]
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-re",                         # 실시간 재생
            "-f", "h264",                  # H.264 입력
            "-i", "pipe:0",                # stdin에서 입력
            "-c:v", "copy",                # 코덱 복사
            "-f", "rtsp",                  # RTSP 출력
            "-rtsp_transport", "tcp",      # TCP 전송
            f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"
        ]
        
        print("🚀 raspivid 시작...")
        print(f"raspivid 명령어: {' '.join(raspivid_cmd)}")
        
        # raspivid 프로세스 시작
        raspivid_process = subprocess.Popen(
            raspivid_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("🚀 FFmpeg 시작...")
        print(f"FFmpeg 명령어: {' '.join(ffmpeg_cmd)}")
        
        # FFmpeg 프로세스 시작 (raspivid의 출력을 입력으로 받음)
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=raspivid_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 프로세스 시작 확인
        time.sleep(5)
        
        if ffmpeg_process.poll() is None and raspivid_process.poll() is None:
            pi_ip = get_raspberry_pi_ip()
            print(f"✅ RTSP 스트림 시작됨!")
            print(f"📺 RTSP URL: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
            print("")
            print("💡 연결 방법:")
            print("   1. VLC 미디어 플레이어 실행")
            print("   2. 미디어 → 네트워크 스트림 열기")
            print("   3. 위 URL 입력 후 재생")
            
            return ffmpeg_process, raspivid_process
        else:
            print("❌ RTSP 스트림 시작 실패")
            return False
            
    except Exception as e:
        print(f"❌ RTSP 스트림 시작 오류: {e}")
        return False

def stop_rtsp_stream(ffmpeg_process, raspivid_process):
    """RTSP 스트림 중지"""
    print("🛑 RTSP 스트림 중지 중...")
    
    if ffmpeg_process:
        ffmpeg_process.terminate()
        try:
            ffmpeg_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_process.kill()
    
    if raspivid_process:
        raspivid_process.terminate()
        try:
            raspivid_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raspivid_process.kill()
    
    print("✅ RTSP 스트림 중지됨")

def signal_handler(sig, frame):
    print("\n🛑 RTSP 스트림 종료 신호 수신")
    sys.exit(0)

def main():
    print("🎥 RaspiRecordSync - RTSP 스트리밍 (라즈베리파이 모듈3 카메라)")
    pi_ip = get_raspberry_pi_ip()
    print(f"라즈베리파이 IP: {pi_ip}")
    
    # 디스코드 알림 초기화
    discord_notifier = None
    try:
        discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
        print("✅ 디스코드 알림 활성화됨")
    except Exception as e:
        print(f"⚠️ 디스코드 알림 초기화 실패: {e}")
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # RTSP 스트림 시작
        result = start_rtsp_stream()
        
        if result:
            ffmpeg_process, raspivid_process = result
            
            # 디스코드 알림
            if discord_notifier:
                discord_notifier.send_rtsp_start_notification(RTSP_PORT, RTSP_PATH)
            
            print("🎥 RTSP 스트림이 실행 중입니다. Ctrl+C로 종료하세요.")
            
            # 스트림 상태 모니터링
            while ffmpeg_process.poll() is None and raspivid_process.poll() is None:
                time.sleep(5)
            
            print("❌ RTSP 스트림이 예기치 않게 종료되었습니다.")
            
            # 디스코드 알림
            if discord_notifier:
                discord_notifier.send_rtsp_stop_notification()
        else:
            print("❌ RTSP 스트림 시작에 실패했습니다.")
            if discord_notifier:
                discord_notifier.send_error_notification("RTSP 스트림 시작 실패")
            
    except KeyboardInterrupt:
        print("\n🛑 RTSP 스트림 중지됨")
    except Exception as e:
        print(f"❌ RTSP 스트림 오류: {e}")
        if discord_notifier:
            discord_notifier.send_error_notification(f"RTSP 스트림 오류: {e}")
    finally:
        if 'ffmpeg_process' in locals() and 'raspivid_process' in locals():
            stop_rtsp_stream(ffmpeg_process, raspivid_process)
        print("👋 RTSP 스트리밍 프로그램 종료")

if __name__ == "__main__":
    main() 