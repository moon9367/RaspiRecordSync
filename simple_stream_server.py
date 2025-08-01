#!/usr/bin/env python3
"""
간단한 HTTP 스트리밍 서버
"""

import http.server
import socketserver
import os
import time
import signal
import sys
from discord_notify import DiscordNotifier

# 서버 설정
PORT = 8080
STREAM_FILE = "/tmp/rtsp_stream.h264"

# 디스코드 웹훅 URL
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1398962742618095667/IVnyN4mNDHGHZxkJ_8b4N-IhIkM95kihJf25ZpXEEHqohY3GC9rOeB4BPyZVnUzXKv_T"

class StreamHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # 메인 페이지
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>라즈베리파이 스트림</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                    .success {{ background-color: #d4edda; color: #155724; }}
                    .error {{ background-color: #f8d7da; color: #721c24; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎥 라즈베리파이 스트림 서버</h1>
                    <div class="status {'success' if os.path.exists(STREAM_FILE) else 'error'}">
                        📁 스트림 파일: {'✅ 존재함' if os.path.exists(STREAM_FILE) else '❌ 없음'}
                    </div>
                    <h2>📺 스트림 URL</h2>
                    <p><strong>HTTP:</strong> <a href="http://localhost:{PORT}/stream">http://localhost:{PORT}/stream</a></p>
                    <p><strong>파일 다운로드:</strong> <a href="http://localhost:{PORT}/download">http://localhost:{PORT}/download</a></p>
                    <h2>💡 사용 방법</h2>
                    <ol>
                        <li>카메라 스트림 시작: <code>python3 camera_stream.py</code></li>
                        <li>VLC에서 네트워크 스트림 열기</li>
                        <li>URL 입력: <code>http://localhost:{PORT}/stream</code></li>
                    </ol>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path == '/stream':
            # 스트림 파일 전송
            if os.path.exists(STREAM_FILE):
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Content-Disposition', 'inline')
                self.end_headers()
                
                with open(STREAM_FILE, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Stream file not found')
                
        elif self.path == '/download':
            # 파일 다운로드
            if os.path.exists(STREAM_FILE):
                file_size = os.path.getsize(STREAM_FILE)
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="stream_{int(time.time())}.h264"')
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                
                with open(STREAM_FILE, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not found')

def signal_handler(sig, frame):
    print("\n🛑 스트림 서버 종료 신호 수신")
    sys.exit(0)

def main():
    print("🌐 HTTP 스트림 서버")
    print(f"📁 스트림 파일: {STREAM_FILE}")
    print(f"🌍 서버 URL: http://localhost:{PORT}")
    
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
        with socketserver.TCPServer(("", PORT), StreamHandler) as httpd:
            print(f"🚀 HTTP 스트림 서버 시작됨: http://localhost:{PORT}")
            
            if discord_notifier:
                discord_notifier.send_message(f"🌐 HTTP 스트림 서버 시작됨: http://localhost:{PORT}")
            
            print("💡 VLC에서 연결하려면:")
            print(f"   http://localhost:{PORT}/stream")
            print("")
            print("💡 카메라 스트림을 시작하려면:")
            print("   python3 camera_stream.py")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 HTTP 스트림 서버 중지됨")
    except Exception as e:
        print(f"❌ HTTP 스트림 서버 오류: {e}")
        if discord_notifier:
            discord_notifier.send_error_notification(f"HTTP 스트림 서버 오류: {e}")
    finally:
        print("👋 HTTP 스트림 서버 종료")

if __name__ == "__main__":
    main() 