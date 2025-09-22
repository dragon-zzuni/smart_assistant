# -*- coding: utf-8 -*-
"""
이메일 기능 테스트 스크립트
"""
import sys
import os
import asyncio
from pathlib import Path

# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_email():
    """이메일 수집 테스트"""
    print("📧 이메일 수집 테스트")
    print("=" * 50)
    
    try:
        from ingestors.email_imap import EmailIMAPCollector
        
        # 테스트 설정 (실제 값으로 변경하세요)
        email_config = {
            "email": "imyongjun@naver.com",
            "password": "X1BEZN9WTXPQ",  # 앱 비밀번호
            "provider": "naver"
        }
        
        print(f"이메일: {email_config['email']}")
        print(f"제공자: {email_config['provider']}")
        
        # 이메일 수집기 생성
        collector = EmailIMAPCollector(
            email_config["email"],
            email_config["password"],
            email_config["provider"]
        )
        
        # 연결 테스트
        print("\n🔌 IMAP 연결 중...")
        if await collector.connect():
            print("✅ IMAP 연결 성공!")
            
            # 미확인 이메일 수집
            print("\n📥 미확인 이메일 수집 중...")
            emails = await collector.get_unread_emails(5)
            
            if emails:
                print(f"✅ {len(emails)}개의 미확인 이메일 수집 성공")
                
                for i, email in enumerate(emails[:3], 1):
                    print(f"\n{i}. 제목: {email.subject}")
                    print(f"   발신자: {email.sender}")
                    print(f"   날짜: {email.date}")
                    print(f"   내용: {email.body[:100]}...")
            else:
                print("📭 미확인 이메일이 없습니다.")
            
            # 연결 종료
            await collector.disconnect()
            print("\n🔌 연결 종료")
            
        else:
            print("❌ IMAP 연결 실패")
            print("   - 이메일 주소와 비밀번호 확인")
            print("   - IMAP 설정 확인")
            print("   - 앱 비밀번호 사용 확인")
    
    except Exception as e:
        print(f"❌ 이메일 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

async def test_full_system():
    """전체 시스템 테스트"""
    print("\n🚀 전체 시스템 테스트")
    print("=" * 50)
    
    try:
        from main import SmartAssistant
        
        assistant = SmartAssistant()
        
        # 이메일 설정 (실제 값으로 변경하세요)
        email_config = {
            "email": "imyongjun@naver.com",
            "password": "X1BEZN9WTXPQ",
            "provider": "naver"
        }
        
        messenger_config = {
            "use_simulator": True
        }
        
        print("시스템 초기화 중...")
        await assistant.initialize(email_config, messenger_config)
        
        print("메시지 수집 중...")
        messages = await assistant.collect_messages(email_limit=3, messenger_limit=3)
        
        if messages:
            print(f"✅ {len(messages)}개 메시지 수집")
            
            print("메시지 분석 중...")
            analysis_results = await assistant.analyze_messages()
            
            if analysis_results:
                print(f"✅ {len(analysis_results)}개 메시지 분석 완료")
                
                print("TODO 리스트 생성 중...")
                todo_list = await assistant.generate_todo_list(analysis_results)
                
                print(f"\n📋 TODO 리스트 생성 완료!")
                print(f"총 {todo_list['total_items']}개 아이템")
                print(f"우선순위: High({todo_list['priority_stats']['high']}), Medium({todo_list['priority_stats']['medium']}), Low({todo_list['priority_stats']['low']})")
                
                print(f"\n🔥 상위 TODO 아이템:")
                for i, item in enumerate(todo_list["items"][:5], 1):
                    print(f"{i}. [{item['priority'].upper()}] {item['title']}")
                    print(f"   요청자: {item['requester']}")
                    if item['deadline']:
                        print(f"   데드라인: {item['deadline']}")
                    print()
            else:
                print("❌ 메시지 분석 실패")
        else:
            print("❌ 메시지 수집 실패")
        
        await assistant.cleanup()
        
    except Exception as e:
        print(f"❌ 전체 시스템 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """메인 테스트 함수"""
    print("🧪 Smart Assistant 테스트 시작")
    print("=" * 50)
    
    # 이메일 테스트
    await test_email()
    
    # 전체 시스템 테스트
    await test_full_system()
    
    print("\n✅ 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
