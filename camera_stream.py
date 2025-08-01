#!/usr/bin/env python3
"""
카메라 스트림 - rpicam-vid를 사용한 카메라 스트림
"""

import subprocess
import time
import signal
import sys
import os
from discord_notify import DiscordNotifier

# 디스코드 웹훅 URL
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1398962742618095667/IVnyN4mNDHGHZxkJ_8b4N-IhIkM95kihJf25ZpXEEHqohY3GC9rOeB4BPyZVnUzXKv_T"

def check_camera_status():
    """카메라 상태 확인"""
    print("=" * 50)
    print("🔍 카메라 상태 확인")
    print("=" * 50)
    
    # rpicam-vid 테스트
    print("📹 rpicam-vid 테스트...")
    try:
        test_cmd = ["rpicam-vid", "-t", "1000", "--output", "/tmp/test.h264"]
        print(f"테스트 명령어: {' '.join(test_cmd)}")
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ rpicam-vid 테스트 성공")
            if os.path.exists("/tmp/test.h264"):
                file_size = os.path.getsize("/tmp/test.h264")
                print(f"✅ 테스트 파일 생성됨: /tmp/test.h264 (크기: {file_size} bytes)")
                os.remove("/tmp/test.h264")  # 테스트 파일 삭제
                return True
            else:
                print("❌ 테스트 파일이 생성되지 않음")
                return False
        else:
            print(f"❌ rpicam-vid 테스트 실패: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("✅ rpicam-vid 테스트 성공 (타임아웃은 정상)")
        if os.path.exists("/tmp/test.h264"):
            file_size = os.path.getsize("/tmp/test.h264")
            print(f"✅ 테스트 파일 생성됨: /tmp/test.h264 (크기: {file_size} bytes)")
            os.remove("/tmp/test.h264")  # 테스트 파일 삭제
            return True
        else:
            print("❌ 테스트 파일이 생성되지 않음")
            return False
    except Exception as e:
        print(f"❌ rpicam-vid 테스트 오류: {e}")
        return False

class CameraStream:
    def __init__(self, discord_notifier=None):
        self.discord_notifier = discord_notifier
        self.camera_process = None
        self.is_running = False
        
    def start_camera_stream(self):
        """카메라 스트림 시작"""
        try:
            print("📹 카메라 스트림 시작 중...")
            
            # 카메라 상태 확인
            if not check_camera_status():
                print("❌ 카메라 상태 확인 실패")
                return False
            
            # rpicam-vid 명령어 (record_realtime_v2.py 참조)
            rpicam_cmd = [
                "rpicam-vid",
                "-t", "0",                     # 무한 실행
                "--codec", "h264",             # H.264 코덱
                "--output", "/tmp/rtsp_stream.h264", # 파일로 출력
                "--width", "1920",             # 너비 (record_realtime_v2.py와 동일)
                "--height", "1080",            # 높이 (record_realtime_v2.py와 동일)
                "--framerate", "30",           # 프레임레이트 (record_realtime_v2.py와 동일)
                "--autofocus-mode", "auto",    # 자동 초점 모드
                "--autofocus-speed", "normal", # 자동 초점 속도
                "--autofocus-range", "normal", # 자동 초점 범위
                "--vflip"                      # 세로 뒤집기
            ]
            
            print(f"rpicam-vid 명령어: {' '.join(rpicam_cmd)}")
            
            # rpicam-vid 프로세스 시작
            self.camera_process = subprocess.Popen(
                rpicam_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 프로세스 시작 확인
            print("⏳ 카메라 스트림 시작 확인 중...")
            time.sleep(5)
            
            if self.camera_process.poll() is None:
                self.is_running = True
                print("✅ 카메라 스트림 시작됨")
                print("📁 스트림 파일: /tmp/rtsp_stream.h264")
                
                if self.discord_notifier:
                    self.discord_notifier.send_notification("카메라 스트림 시작됨")
                
                return True
            else:
                print("❌ 카메라 스트림 시작 실패")
                # 오류 메시지 출력
                try:
                    stdout, stderr = self.camera_process.communicate(timeout=1)
                    if stderr:
                        print(f"rpicam-vid 오류: {stderr.decode('utf-8', errors='ignore')}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ 카메라 스트림 시작 실패: {e}")
            return False
    
    def stop_camera_stream(self):
        """카메라 스트림 중지"""
        if self.camera_process:
            print("🛑 카메라 스트림 중지 중...")
            self.camera_process.terminate()
            try:
                self.camera_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.camera_process.kill()
        
        self.is_running = False
        print("✅ 카메라 스트림 중지됨")
        
        if self.discord_notifier:
            self.discord_notifier.send_notification("카메라 스트림 중지됨")
    
    def check_stream_status(self):
        """카메라 스트림 상태 확인"""
        if self.camera_process:
            return self.camera_process.poll() is None
        return False

def signal_handler(sig, frame):
    print("\n🛑 카메라 스트림 종료 신호 수신")
    sys.exit(0)

def main():
    print("📹 카메라 스트림")
    
    # 디스코드 알림 초기화
    discord_notifier = None
    try:
        discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
        print("✅ 디스코드 알림 활성화됨")
    except Exception as e:
        print(f"⚠️ 디스코드 알림 초기화 실패: {e}")
    
    # 카메라 스트림 초기화
    camera_stream = CameraStream(discord_notifier)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 카메라 스트림 시작
        if camera_stream.start_camera_stream():
            print("📹 카메라 스트림이 실행 중입니다.")
            print("📁 스트림 파일: /tmp/rtsp_stream.h264")
            print("")
            print("💡 RTSP 서버를 시작하려면:")
            print("   python3 rtsp_server.py")
            
            # 스트림 상태 모니터링
            while camera_stream.check_stream_status():
                time.sleep(5)
            
            print("❌ 카메라 스트림이 예기치 않게 종료되었습니다.")
        else:
            print("❌ 카메라 스트림 시작에 실패했습니다.")
            
    except KeyboardInterrupt:
        print("\n🛑 카메라 스트림 중지됨")
    except Exception as e:
        print(f"❌ 카메라 스트림 오류: {e}")
        if discord_notifier:
            discord_notifier.send_error_notification(f"카메라 스트림 오류: {e}")
    finally:
        camera_stream.stop_camera_stream()
        print("👋 카메라 스트림 종료")

if __name__ == "__main__":
    main() 