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

def check_camera_status():
    """카메라 상태 상세 확인"""
    print("=" * 50)
    print("🔍 카메라 상태 상세 확인 시작")
    print("=" * 50)
    
    # 1. vcgencmd로 카메라 상태 확인
    print("1️⃣ vcgencmd 카메라 상태 확인...")
    try:
        result = subprocess.run(["vcgencmd", "get_camera"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ vcgencmd 결과: {result.stdout.strip()}")
        else:
            print(f"❌ vcgencmd 실패: {result.stderr.strip()}")
    except Exception as e:
        print(f"❌ vcgencmd 오류: {e}")
    
    # 2. /dev/video* 장치 확인
    print("\n2️⃣ /dev/video* 장치 확인...")
    try:
        result = subprocess.run(["ls", "-la", "/dev/video*"], capture_output=True, text=True)
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')
            print(f"✅ 발견된 비디오 장치:")
            for device in devices:
                print(f"   {device}")
        else:
            print(f"❌ 비디오 장치 확인 실패: {result.stderr.strip()}")
    except Exception as e:
        print(f"❌ 비디오 장치 확인 오류: {e}")
    
    # 3. rpicam-vid 테스트 (최신 라즈베리파이 OS용)
    print("\n3️⃣ rpicam-vid 명령어 테스트...")
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
            else:
                print("❌ 테스트 파일이 생성되지 않음")
        else:
            print(f"❌ rpicam-vid 테스트 실패: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("✅ rpicam-vid 테스트 성공 (타임아웃은 정상)")
        if os.path.exists("/tmp/test.h264"):
            file_size = os.path.getsize("/tmp/test.h264")
            print(f"✅ 테스트 파일 생성됨: /tmp/test.h264 (크기: {file_size} bytes)")
            os.remove("/tmp/test.h264")  # 테스트 파일 삭제
    except Exception as e:
        print(f"❌ rpicam-vid 테스트 오류: {e}")
    
    # 4. ffmpeg 테스트
    print("\n4️⃣ ffmpeg 테스트...")
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ffmpeg 설치됨")
            # 첫 번째 줄만 출력
            version_line = result.stdout.split('\n')[0]
            print(f"   {version_line}")
        else:
            print(f"❌ ffmpeg 확인 실패: {result.stderr.strip()}")
    except Exception as e:
        print(f"❌ ffmpeg 확인 오류: {e}")
    
    # 5. 카메라 설정 확인
    print("\n5️⃣ 카메라 설정 확인...")
    print("💡 카메라가 인식되지 않는 경우 다음을 확인하세요:")
    print("   1. sudo raspi-config 실행")
    print("   2. Interface Options → Camera → Enable")
    print("   3. 라즈베리파이 재부팅")
    print("   4. 카메라 모듈이 제대로 연결되어 있는지 확인")
    
    print("=" * 50)
    print("🔍 카메라 상태 확인 완료")
    print("=" * 50)

class RTSPStreamer:
    def __init__(self, discord_notifier=None):
        self.discord_notifier = discord_notifier
        self.rtsp_process = None
        self.video_process = None
        self.is_running = False
        
    def start_rtsp_stream(self):
        """RTSP 스트림 시작 - 라즈베리파이 모듈3 카메라용"""
        try:
            print(f"🎥 RTSP 스트림 시작: {RTSP_URL}")
            
            # 카메라 상태 상세 확인
            check_camera_status()
            
            # 사용 가능한 비디오 장치 확인
            print("\n🔍 사용 가능한 비디오 장치 확인 중...")
            try:
                result = subprocess.run(["ls", "/dev/video*"], capture_output=True, text=True)
                if result.returncode == 0:
                    devices = result.stdout.strip().split('\n')
                    print(f"📹 발견된 비디오 장치: {devices}")
                    
                    # 첫 번째 장치 사용
                    video_device = devices[0] if devices else "/dev/video0"
                    print(f"🎥 사용할 장치: {video_device}")
                else:
                    video_device = "/dev/video0"
                    print(f"⚠️ 장치 확인 실패, 기본값 사용: {video_device}")
            except Exception as e:
                video_device = "/dev/video0"
                print(f"⚠️ 장치 확인 오류, 기본값 사용: {video_device}")
            
            # 방법 1: rpicam-vid + ffmpeg 직접 파이프라인
            print("\n" + "=" * 50)
            print("🚀 RTSP 스트리밍 시작...")
            print("=" * 50)
            
            # rpicam-vid + ffmpeg 파이프라인
            rpicam_cmd = [
                "rpicam-vid",
                "-t", "0",                     # 무한 실행
                "--codec", "h264",             # H.264 코덱
                "--width", "1280",             # 너비
                "--height", "720",             # 높이
                "--framerate", "25",           # 프레임레이트
                "--bitrate", "2500000",        # 비트레이트
                "--output", "stdout",          # stdout으로 출력
                "--inline",                    # 인라인 헤더
                "--nopreview"                  # 미리보기 비활성화
            ]
            
            ffmpeg_rtsp_cmd = [
                "ffmpeg",
                "-re",                         # 실시간 재생
                "-f", "h264",                  # H.264 입력
                "-i", "pipe:0",                # stdin에서 입력
                "-c:v", "copy",                # 코덱 복사
                "-f", "rtsp",                  # RTSP 출력
                "-rtsp_transport", "tcp",      # TCP 전송
                "-listen", "1",                # RTSP 서버 모드
                "-analyzeduration", "1000000", # 분석 시간 (1초)
                "-probesize", "10000000",      # 프로브 크기 (10MB)
                f"rtsp://0.0.0.0:{RTSP_PORT}/{RTSP_PATH}"
            ]
            
            try:
                print("🚀 rpicam-vid + ffmpeg 파이프라인 시작...")
                print(f"rpicam-vid 명령어: {' '.join(rpicam_cmd)}")
                print(f"ffmpeg 명령어: {' '.join(ffmpeg_rtsp_cmd)}")
                
                # rpicam-vid 프로세스 시작
                print("📹 rpicam-vid 프로세스 시작 중...")
                self.video_process = subprocess.Popen(
                    rpicam_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                print("✅ rpicam-vid 프로세스 시작됨")
                
                # ffmpeg 프로세스 시작 (rpicam-vid의 출력을 입력으로 받음)
                print("📺 FFmpeg 프로세스 시작 중...")
                self.rtsp_process = subprocess.Popen(
                    ffmpeg_rtsp_cmd,
                    stdin=self.video_process.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                print("✅ FFmpeg 프로세스 시작됨")
                
                # 프로세스 시작 확인
                print("⏳ 프로세스 상태 확인 중...")
                time.sleep(5)
                
                rpicam_status = self.video_process.poll()
                ffmpeg_status = self.rtsp_process.poll()
                
                print(f"rpicam-vid 상태: {'실행 중' if rpicam_status is None else f'종료됨 (코드: {rpicam_status})'}")
                print(f"ffmpeg 상태: {'실행 중' if ffmpeg_status is None else f'종료됨 (코드: {ffmpeg_status})'}")
                
                if ffmpeg_status is None and rpicam_status is None:
                    self.is_running = True
                    pi_ip = get_raspberry_pi_ip()
                    print(f"✅ RTSP 스트림 시작됨: rtsp://{pi_ip}:{RTSP_PORT}/{RTSP_PATH}")
                    
                    if self.discord_notifier:
                        self.discord_notifier.send_rtsp_start_notification(RTSP_PORT, RTSP_PATH)
                    
                    return True
                else:
                    print("❌ RTSP 스트림 시작 실패")
                    # 오류 메시지 출력
                    try:
                        if rpicam_status is not None:
                            stdout, stderr = self.video_process.communicate(timeout=1)
                            if stderr:
                                print(f"rpicam-vid 오류: {stderr.decode('utf-8', errors='ignore')}")
                        if ffmpeg_status is not None:
                            stdout, stderr = self.rtsp_process.communicate(timeout=1)
                            if stderr:
                                print(f"ffmpeg 오류: {stderr.decode('utf-8', errors='ignore')}")
                    except:
                        pass
                    return False
                    
            except Exception as e:
                print(f"⚠️ RTSP 스트림 시작 실패: {e}")
                return False
                
        except Exception as e:
            print(f"❌ RTSP 스트림 시작 실패: {e}")
            if self.discord_notifier:
                self.discord_notifier.send_error_notification(f"RTSP 스트림 시작 실패: {e}")
            return False
    
    def stop_rtsp_stream(self):
        """RTSP 스트림 중지"""
        if hasattr(self, 'rtsp_process') and self.rtsp_process:
            print("🛑 RTSP 스트림 중지 중...")
            self.rtsp_process.terminate()
            try:
                self.rtsp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.rtsp_process.kill()
        
        if hasattr(self, 'video_process') and self.video_process:
            print("🛑 비디오 캡처 중지 중...")
            self.video_process.terminate()
            try:
                self.video_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.video_process.kill()
        
        # 임시 파일 정리
        try:
            if os.path.exists("/tmp/rtsp_stream.h264"):
                os.remove("/tmp/rtsp_stream.h264")
                print("🗑️ 임시 파일 정리됨")
        except:
            pass
        
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
    print("🎥 RaspiRecordSync - RTSP 스트리밍 서버 (라즈베리파이 모듈3 카메라용)")
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