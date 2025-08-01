#!/usr/bin/env python3
"""
RTSP 서버 - FFmpeg를 사용한 RTSP 서버
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

class RTSPServer:
    def __init__(self, discord_notifier=None):
        self.discord_notifier = discord_notifier
        self.rtsp_process = None
        self.is_running = False
        
    def start_rtsp_server(self):
        """RTSP 서버 시작"""
        try:
            print("🚀 RTSP 서버 시작 중...")
            
            # FFmpeg RTSP 서버 명령어
            ffmpeg_cmd = [
                "ffmpeg",
                "-re",                         # 실시간 재생
                "-f", "h264",                  # H.264 입력
                "-i", "/tmp/rtsp_stream.h264", # 파일 입력
                "-c:v", "copy",                # 코덱 복사
                "-f", "rtsp",                  # RTSP 출력
                "-rtsp_transport", "tcp",      # TCP 전송
                "-listen", "1",                # RTSP 서버 모드
                "-analyzeduration", "1000000", # 분석 시간 (1초)
                "-probesize", "10000000",      # 프로브 크기 (10MB)
                f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"
            ]
            
            print(f"FFmpeg 명령어: {' '.join(ffmpeg_cmd)}")
            
            # FFmpeg 프로세스 시작
            self.rtsp_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 프로세스 시작 확인
            print("⏳ RTSP 서버 시작 확인 중...")
            time.sleep(3)
            
            if self.rtsp_process.poll() is None:
                self.is_running = True
                pi_ip = get_raspberry_pi_ip()
                print(f"✅ RTSP 서버 시작됨: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
                
                if self.discord_notifier:
                    self.discord_notifier.send_rtsp_start_notification(RTSP_PORT, RTSP_PATH)
                
                return True
            else:
                print("❌ RTSP 서버 시작 실패")
                # 오류 메시지 출력
                try:
                    stdout, stderr = self.rtsp_process.communicate(timeout=1)
                    if stderr:
                        print(f"FFmpeg 오류: {stderr.decode('utf-8', errors='ignore')}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ RTSP 서버 시작 실패: {e}")
            return False
    
    def stop_rtsp_server(self):
        """RTSP 서버 중지"""
        if self.rtsp_process:
            print("🛑 RTSP 서버 중지 중...")
            self.rtsp_process.terminate()
            try:
                self.rtsp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.rtsp_process.kill()
        
        self.is_running = False
        print("✅ RTSP 서버 중지됨")
        
        if self.discord_notifier:
            self.discord_notifier.send_rtsp_stop_notification()
    
    def check_server_status(self):
        """RTSP 서버 상태 확인"""
        if self.rtsp_process:
            return self.rtsp_process.poll() is None
        return False

def signal_handler(sig, frame):
    print("\n🛑 RTSP 서버 종료 신호 수신")
    sys.exit(0)

def main():
    print("🎥 RTSP 서버")
    pi_ip = get_raspberry_pi_ip()
    print(f"RTSP URL: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
    
    # 디스코드 알림 초기화
    discord_notifier = None
    try:
        discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
        print("✅ 디스코드 알림 활성화됨")
    except Exception as e:
        print(f"⚠️ 디스코드 알림 초기화 실패: {e}")
    
    # RTSP 서버 초기화
    rtsp_server = RTSPServer(discord_notifier)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # RTSP 서버 시작
        if rtsp_server.start_rtsp_server():
            print("🎥 RTSP 서버가 실행 중입니다.")
            print(f"📺 VLC나 다른 RTSP 클라이언트로 연결하세요:")
            print(f"   rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
            print("")
            print("💡 연결 방법:")
            print("   1. VLC 미디어 플레이어 실행")
            print("   2. 미디어 → 네트워크 스트림 열기")
            print("   3. 위 URL 입력 후 재생")
            print("")
            print("📝 카메라 스트림을 시작하려면:")
            print("   python3 camera_stream.py")
            
            # 서버 상태 모니터링
            while rtsp_server.check_server_status():
                time.sleep(5)
            
            print("❌ RTSP 서버가 예기치 않게 종료되었습니다.")
        else:
            print("❌ RTSP 서버 시작에 실패했습니다.")
            
    except KeyboardInterrupt:
        print("\n🛑 RTSP 서버 중지됨")
    except Exception as e:
        print(f"❌ RTSP 서버 오류: {e}")
        if discord_notifier:
            discord_notifier.send_error_notification(f"RTSP 서버 오류: {e}")
    finally:
        rtsp_server.stop_rtsp_server()
        print("👋 RTSP 서버 종료")

if __name__ == "__main__":
    main() 