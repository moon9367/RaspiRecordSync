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
                    "value": "30분마다 영상 촬영",
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
        return self.send_message("🛑 시스템 종료됨", embed)
    
    def send_ssh_upload_complete(self, filename, file_size_mb, server_host, upload_time=None):
        """SSH 업로드 완료 알림"""
        if upload_time is None:
            upload_time = datetime.datetime.now().strftime('%H:%M:%S')
            
        embed = {
            "title": "📤 SSH 업로드 완료",
            "description": f"파일이 SSH를 통해 원격 서버로 전송되었습니다.",
            "color": 0x00ff00,  # 초록색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📁 파일명",
                    "value": filename,
                    "inline": False
                },
                {
                    "name": "📊 파일 크기",
                    "value": f"{file_size_mb:.1f} MB",
                    "inline": True
                },
                {
                    "name": "🌐 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "⏰ 업로드 시간",
                    "value": upload_time,
                    "inline": True
                }
            ]
        }
        return self.send_message("✅ SSH 업로드 완료", embed)
    
    def send_ssh_upload_error(self, filename, error_message, server_host):
        """SSH 업로드 오류 알림"""
        embed = {
            "title": "❌ SSH 업로드 실패",
            "description": f"SSH를 통한 파일 업로드에 실패했습니다.",
            "color": 0xff0000,  # 빨간색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📁 파일명",
                    "value": filename,
                    "inline": True
                },
                {
                    "name": "🌐 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "❌ 오류 내용",
                    "value": error_message[:1000] + "..." if len(error_message) > 1000 else error_message,
                    "inline": False
                }
            ]
        }
        return self.send_message("🚨 SSH 업로드 실패", embed)
    
    def send_ssh_connection_test(self, server_host, server_user, status="성공"):
        """SSH 연결 테스트 결과 알림"""
        color = 0x00ff00 if status == "성공" else 0xff0000
        status_emoji = "✅" if status == "성공" else "❌"
        
        embed = {
            "title": f"{status_emoji} SSH 연결 테스트",
            "description": f"SSH 연결 테스트 결과: {status}",
            "color": color,
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "🌐 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "👤 사용자",
                    "value": server_user,
                    "inline": True
                },
                {
                    "name": "📊 상태",
                    "value": status,
                    "inline": True
                }
            ]
        }
        return self.send_message(f"{status_emoji} SSH 연결 테스트", embed)
    
    def send_ssh_system_start(self, server_host, server_user, remote_path):
        """SSH 시스템 시작 알림"""
        embed = {
            "title": "🚀 SSH 동기화 시스템 시작",
            "description": "SSH를 통한 파일 동기화 시스템이 시작되었습니다.",
            "color": 0x0099ff,  # 파란색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "🌐 원격 서버",
                    "value": f"{server_user}@{server_host}",
                    "inline": True
                },
                {
                    "name": "📁 원격 경로",
                    "value": remote_path,
                    "inline": True
                },
                {
                    "name": "🔄 동기화 방식",
                    "value": "SSH rsync",
                    "inline": True
                }
            ]
        }
        return self.send_message("🚀 SSH 동기화 시스템 시작됨", embed)
    
    def send_webdav_upload_complete(self, filename, file_size_mb, server_host, upload_time=None):
        """WebDAV 업로드 완료 알림"""
        if upload_time is None:
            upload_time = datetime.datetime.now().strftime('%H:%M:%S')
            
        embed = {
            "title": "📤 WebDAV 업로드 완료",
            "description": f"파일이 WebDAV를 통해 원격 서버로 전송되었습니다.",
            "color": 0x00ff00,  # 초록색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📁 파일명",
                    "value": filename,
                    "inline": False
                },
                {
                    "name": "📊 파일 크기",
                    "value": f"{file_size_mb:.1f} MB",
                    "inline": True
                },
                {
                    "name": "🌐 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "⏰ 업로드 시간",
                    "value": upload_time,
                    "inline": True
                }
            ]
        }
        return self.send_message("✅ WebDAV 업로드 완료", embed)
    
    def send_webdav_upload_error(self, filename, error_message, server_host):
        """WebDAV 업로드 오류 알림"""
        embed = {
            "title": "❌ WebDAV 업로드 실패",
            "description": f"WebDAV를 통한 파일 업로드에 실패했습니다.",
            "color": 0xff0000,  # 빨간색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📁 파일명",
                    "value": filename,
                    "inline": True
                },
                {
                    "name": "🌐 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "❌ 오류 내용",
                    "value": error_message[:1000] + "..." if len(error_message) > 1000 else error_message,
                    "inline": False
                }
            ]
        }
        return self.send_message("🚨 WebDAV 업로드 실패", embed)
    
    def send_webdav_system_start(self, server_host, server_user, remote_path):
        """WebDAV 시스템 시작 알림"""
        embed = {
            "title": "🚀 WebDAV 동기화 시스템 시작",
            "description": "WebDAV를 통한 파일 동기화 시스템이 시작되었습니다.",
            "color": 0x0099ff,  # 파란색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "🌐 WebDAV 서버",
                    "value": server_host,
                    "inline": True
                },
                {
                    "name": "👤 사용자",
                    "value": server_user,
                    "inline": True
                },
                {
                    "name": "📁 원격 경로",
                    "value": remote_path,
                    "inline": True
                },
                {
                    "name": "🔄 동기화 방식",
                    "value": "WebDAV HTTP",
                    "inline": True
                }
            ]
        }
        return self.send_message("🚀 WebDAV 동기화 시스템 시작됨", embed)
    
    def send_rtsp_start_notification(self, rtsp_port, rtsp_path):
        """RTSP 스트림 시작 알림"""
        embed = {
            "title": "🎥 RTSP 스트림 시작",
            "description": "RTSP 실시간 스트리밍이 시작되었습니다.",
            "color": 0x00ff00,  # 초록색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📺 RTSP URL",
                    "value": f"rtsp://[라즈베리파이IP]:{rtsp_port}/{rtsp_path}",
                    "inline": False
                },
                {
                    "name": "🔌 포트",
                    "value": str(rtsp_port),
                    "inline": True
                },
                {
                    "name": "📡 프로토콜",
                    "value": "RTSP/TCP",
                    "inline": True
                },
                {
                    "name": "🎬 해상도",
                    "value": "1280x720",
                    "inline": True
                }
            ]
        }
        return self.send_message("🎥 RTSP 스트림 시작됨", embed)
    
    def send_rtsp_stop_notification(self):
        """RTSP 스트림 종료 알림"""
        embed = {
            "title": "🛑 RTSP 스트림 종료",
            "description": "RTSP 실시간 스트리밍이 종료되었습니다.",
            "color": 0xff9900,  # 주황색
            "timestamp": datetime.datetime.now().isoformat()
        }
        return self.send_message("🛑 RTSP 스트림 종료됨", embed)
    
    def send_system_log_summary(self, log_data, period_minutes=30):
        """시스템 로그 요약 전송"""
        if not log_data:
            return False
            
        # 통계 계산
        cpu_percentages = [float(row['cpu_percent']) for row in log_data]
        cpu_temps = [float(row['cpu_temp']) for row in log_data]
        
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        max_cpu = max(cpu_percentages)
        min_cpu = min(cpu_percentages)
        
        avg_temp = sum(cpu_temps) / len(cpu_temps)
        max_temp = max(cpu_temps)
        min_temp = min(cpu_temps)
        
        embed = {
            "title": "📊 시스템 모니터링 리포트",
            "description": f"지난 {period_minutes}분간의 시스템 상태 요약",
            "color": 0x0099ff,  # 파란색
            "timestamp": datetime.datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📈 CPU 사용률",
                    "value": f"평균: {avg_cpu:.1f}%\n최대: {max_cpu:.1f}%\n최소: {min_cpu:.1f}%",
                    "inline": True
                },
                {
                    "name": "🌡️ CPU 온도",
                    "value": f"평균: {avg_temp:.1f}°C\n최대: {max_temp:.1f}°C\n최소: {min_temp:.1f}°C",
                    "inline": True
                },
                {
                    "name": "📊 데이터 포인트",
                    "value": f"{len(log_data)}개",
                    "inline": True
                }
            ]
        }
        return self.send_message("📊 시스템 모니터링 리포트", embed)