# -*- coding: utf-8 -*-
"""
Smart Assistant 실행 스크립트
"""
import asyncio
import sys
import os
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

# 로깅 설정 (간단하게)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from main import SmartAssistant


async def main():
    """메인 실행 함수"""
    print("🚀 Smart Assistant 실행 중...")
    print("=" * 50)
    
    # 설정 입력 받기
    print("📧 이메일 설정:")
    email = input("이메일 주소 (예: imyongjun@naver.com): ").strip()
    if not email:
        email = "imyongjun@naver.com"  # 기본값
    
    password = input("비밀번호/앱 비밀번호: ").strip()
    if not password:
        password = "X1BEZN9WTXPQ"  # 기본값 (실제 사용 시 환경변수 권장)
    
    provider = input("이메일 제공자 (naver/gmail, 기본값: naver): ").strip().lower()
    if not provider:
        provider = "naver"
    
    print(f"\n📱 메신저 설정:")
    use_simulator = input("시뮬레이터 사용? (y/n, 기본값: y): ").strip().lower()
    use_simulator = use_simulator != 'n'
    
    print(f"\n📊 수집 설정:")
    email_limit = input("이메일 수집 개수 (기본값: 10): ").strip()
    email_limit = int(email_limit) if email_limit.isdigit() else 10
    
    messenger_limit = input("메신저 메시지 수집 개수 (기본값: 10): ").strip()
    messenger_limit = int(messenger_limit) if messenger_limit.isdigit() else 10
    
    # 설정 구성
    email_config = {
        "email": email,
        "password": password,
        "provider": provider
    }
    
    messenger_config = {
        "use_simulator": use_simulator
    }
    
    print(f"\n🔧 설정 완료:")
    print(f"   이메일: {email}")
    print(f"   제공자: {provider}")
    print(f"   이메일 수집: {email_limit}개")
    print(f"   메신저 수집: {messenger_limit}개")
    print(f"   시뮬레이터: {'사용' if use_simulator else '미사용'}")
    
    input(f"\n⏸️  계속하려면 Enter를 누르세요...")
    
    # Smart Assistant 실행
    assistant = SmartAssistant()
    
    try:
        result = await assistant.run_full_cycle(email_config, messenger_config)
        
        if result.get("success"):
            todo_list = result["todo_list"]
            
            print(f"\n✅ Smart Assistant 실행 완료!")
            print(f"=" * 50)
            print(f"📊 수집 결과:")
            print(f"   총 메시지: {result['collected_messages']}개")
            print(f"   TODO 아이템: {todo_list['total_items']}개")
            print(f"   우선순위: High({todo_list['priority_stats']['high']}), Medium({todo_list['priority_stats']['medium']}), Low({todo_list['priority_stats']['low']})")
            
            print(f"\n🔥 상위 TODO 아이템:")
            for i, item in enumerate(todo_list["items"][:10], 1):
                print(f"{i:2d}. [{item['priority'].upper():5s}] {item['title']}")
                print(f"     요청자: {item['requester']}")
                if item['deadline']:
                    print(f"     데드라인: {item['deadline']}")
                print(f"     타입: {item['type']}")
                print()
            
            # 결과 저장
            save_result = input(f"\n💾 결과를 JSON 파일로 저장하시겠습니까? (y/n): ").strip().lower()
            if save_result == 'y':
                import json
                from datetime import datetime
                
                filename = f"assistant_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 결과가 {filename}에 저장되었습니다.")
        
        else:
            print(f"❌ 실행 실패: {result.get('error')}")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
    
    finally:
        await assistant.cleanup()
        print(f"\n👋 Smart Assistant를 종료합니다.")


if __name__ == "__main__":
    asyncio.run(main())
