import requests
import json
import datetime

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        
    def send_message(self, content, embed=None):
        """디스코드로 메시지 전송"""
        try:
            payload = {"content": content}
            if embed:
                payload["embeds"] = [embed]
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 204:
                print(f"✅ 디스코드 알림 전송 성공")
                return True
            else:
                print(f"❌ 디스코드 알림 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 디스코드 알림 오류: {e}")
            return False
    
    def send_start_notification(self):
        """시스템 시작 알림"""
        embed = {
            "title": "🎬 RaspiRecordSync 시작",
            "description": "실시간 녹화 시스템이 시작되었습니다.",
            "color": 0x00ff00,  # 초록색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📹 녹화 설정",
                    "value": "1시간마다 영상 촬영",
                    "inline": True
                },
                {
                    "name": "📊 모니터링",
                    "value": "CPU 사용률 및 온도 기록",
                    "inline": True
                }
            ]
        }
        return self.send_message("🚀 시스템 시작됨", embed)
    
    def send_recording_complete(self, filename, timestamp, cpu_percent, cpu_temp):
        """녹화 완료 알림"""
        embed = {
            "title": "✅ 녹화 완료",
            "description": f"새로운 영상이 저장되었습니다.",
            "color": 0x0099ff,  # 파란색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📁 파일명",
                    "value": filename,
                    "inline": False
                },
                {
                    "name": "⏰ 촬영 시간",
                    "value": timestamp,
                    "inline": True
                },
                {
                    "name": "💻 CPU 사용률",
                    "value": f"{cpu_percent:.1f}%",
                    "inline": True
                },
                {
                    "name": "🌡️ CPU 온도",
                    "value": f"{cpu_temp:.1f}°C",
                    "inline": True
                }
            ]
        }
        return self.send_message("📹 녹화 완료", embed)
    
    def send_error_notification(self, error_message):
        """오류 알림"""
        embed = {
            "title": "❌ 시스템 오류",
            "description": error_message,
            "color": 0xff0000,  # 빨간색
            "timestamp": datetime.datetime.now().isoformat()
        }
        return self.send_message("🚨 오류 발생", embed)
    
    def send_stop_notification(self):
        """시스템 종료 알림"""
        embed = {
            "title": "🛑 RaspiRecordSync 종료",
            "description": "실시간 녹화 시스템이 종료되었습니다.",
            "color": 0xff9900,  # 주황색
            "timestamp": datetime.datetime.now().isoformat()
        }
        return self.send_message("�� 시스템 종료됨", embed) 