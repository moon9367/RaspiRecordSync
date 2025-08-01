import subprocess
import threading
import time
import signal
import sys
import os
import socket
from discord_notify import DiscordNotifier

# RTSP 설정
RTSP_PORT = 8554
RTSP_PATH = "live"
RTSP_URL = f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"

# 디스코드 웹훅 URL (기존과 동일)
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1398962742618095667/IVnyN4mNDHGHZxkJ_8b4N-IhIkM95kihJf25ZpXEEHqohY3GC9rOeB4BPyZVnUzXKv_T"

def get_raspberry_pi_ip():
    """라즈베리파이 IP 주소 가져오기"""
    try:
        # 외부 연결을 통해 IP 확인
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "라즈베리파이IP"

class RTSPStreamer:
    def __init__(self, discord_notifier=None):
        self.discord_notifier = discord_notifier
        self.rtsp_process = None
        self.is_running = False
        
    def start_rtsp_stream(self):
        """RTSP 스트림 시작 - 간단한 방법"""
        try:
            print(f"🎥 RTSP 스트림 시작: {RTSP_URL}")
            
            # 방법 1: rpicam-vid를 직접 RTSP로 스트리밍 (수정된 버전)
            rtsp_cmd = [
                "rpicam-vid",
                "--inline",                      # 인라인 헤더
                "--codec", "h264",              # H.264 코덱
                "--width", "1280",              # 너비
                "--height", "720",              # 높이
                "--framerate", "25",            # 프레임레이트
                "--bitrate", "2500000",         # 비트레이트 (2.5Mbps)
                "--profile", "baseline",        # 베이스라인 프로파일
                "--level", "3.1",               # 레벨
                "--intra", "25",                # I-프레임 간격
                "--output", "-",                # stdout으로 출력
                "|", "ffmpeg",                  # 파이프로 FFmpeg에 전달
                "-f", "h264",                   # 입력 포맷 지정
                "-i", "-",                      # stdin에서 입력
                "-c:v", "copy",                 # 코덱 복사
                "-f", "rtsp",                   # RTSP 출력
                "-rtsp_transport", "tcp",       # TCP 전송
                f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"
            ]
            
            # 방법 2: FFmpeg만 사용 (백업)
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "v4l2",                   # Video4Linux2 입력
                "-i", "/dev/video0",            # 카메라 장치
                "-c:v", "libx264",              # H.264 코덱
                "-preset", "ultrafast",         # 빠른 인코딩
                "-tune", "zerolatency",         # 지연 최소화
                "-b:v", "2500k",                # 비트레이트
                "-maxrate", "2500k",            # 최대 비트레이트
                "-bufsize", "5000k",            # 버퍼 크기
                "-pix_fmt", "yuv420p",          # 픽셀 포맷
                "-g", "25",                     # GOP 크기
                "-f", "rtsp",                   # RTSP 출력
                "-rtsp_transport", "tcp",       # TCP 전송
                f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"
            ]
            
            # rpicam-vid 사용 시도
            try:
                print("🚀 rpicam-vid를 사용한 RTSP 스트림 시작...")
                cmd_str = " ".join(rtsp_cmd)
                print(f"실행 명령어: {cmd_str}")
                self.rtsp_process = subprocess.Popen(
                    cmd_str,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except Exception as e:
                print(f"⚠️ rpicam-vid 실패, FFmpeg 사용: {e}")
                print("🚀 FFmpeg를 사용한 RTSP 스트림 시작...")
                print(f"FFmpeg 명령어: {' '.join(ffmpeg_cmd)}")
                self.rtsp_process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # 프로세스 시작 확인
            time.sleep(3)
            if self.rtsp_process.poll() is None:
                self.is_running = True
                pi_ip = get_raspberry_pi_ip()
                print(f"✅ RTSP 스트림 시작됨: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
                
                # 디스코드 알림
                if self.discord_notifier:
                    self.discord_notifier.send_rtsp_start_notification(RTSP_PORT, RTSP_PATH)
                
                return True
            else:
                print("❌ RTSP 스트림 시작 실패")
                # 오류 메시지 출력
                try:
                    stdout, stderr = self.rtsp_process.communicate(timeout=1)
                    if stderr:
                        print(f"오류 메시지: {stderr.decode('utf-8', errors='ignore')}")
                    if stdout:
                        print(f"출력 메시지: {stdout.decode('utf-8', errors='ignore')}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ RTSP 스트림 시작 실패: {e}")
            if self.discord_notifier:
                self.discord_notifier.send_error_notification(f"RTSP 스트림 시작 실패: {e}")
            return False
    
    def stop_rtsp_stream(self):
        """RTSP 스트림 중지"""
        if self.rtsp_process:
            print("🛑 RTSP 스트림 중지 중...")
            self.rtsp_process.terminate()
            try:
                self.rtsp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.rtsp_process.kill()
            self.is_running = False
            print("✅ RTSP 스트림 중지됨")
            
            if self.discord_notifier:
                self.discord_notifier.send_rtsp_stop_notification()
    
    def check_rtsp_status(self):
        """RTSP 스트림 상태 확인"""
        if self.rtsp_process:
            return self.rtsp_process.poll() is None
        return False

def signal_handler(sig, frame):
    print("\n🛑 RTSP 스트림 종료 신호 수신")
    sys.exit(0)

def main():
    print("🎥 RaspiRecordSync - RTSP 스트리밍 서버 (간단 버전)")
    pi_ip = get_raspberry_pi_ip()
    print(f"RTSP URL: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
    
    # 디스코드 알림 초기화
    discord_notifier = None
    try:
        discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
        print("✅ 디스코드 알림 활성화됨")
    except Exception as e:
        print(f"⚠️ 디스코드 알림 초기화 실패: {e}")
    
    # RTSP 스트리머 초기화
    rtsp_streamer = RTSPStreamer(discord_notifier)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # RTSP 스트림 시작
        if rtsp_streamer.start_rtsp_stream():
            print("🎥 RTSP 스트림이 실행 중입니다.")
            print(f"📺 VLC나 다른 RTSP 클라이언트로 연결하세요:")
            print(f"   rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
            print("")
            print("💡 연결 방법:")
            print("   1. VLC 미디어 플레이어 실행")
            print("   2. 미디어 → 네트워크 스트림 열기")
            print("   3. 위 URL 입력 후 재생")
            
            # 스트림 상태 모니터링
            while rtsp_streamer.check_rtsp_status():
                time.sleep(5)
            
            print("❌ RTSP 스트림이 예기치 않게 종료되었습니다.")
        else:
            print("❌ RTSP 스트림 시작에 실패했습니다.")
            
    except KeyboardInterrupt:
        print("\n🛑 RTSP 스트림 중지됨")
    except Exception as e:
        print(f"❌ RTSP 스트림 오류: {e}")
        if discord_notifier:
            discord_notifier.send_error_notification(f"RTSP 스트림 오류: {e}")
    finally:
        rtsp_streamer.stop_rtsp_stream()
        print("👋 RTSP 스트리밍 프로그램 종료")

if __name__ == "__main__":
    main() 