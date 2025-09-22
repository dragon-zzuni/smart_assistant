# -*- coding: utf-8 -*-
"""
Smart Assistant 데모 스크립트
실제 사용 예시를 보여주는 데모
"""
import sys
import os
import asyncio
import json
from datetime import datetime
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

from main import SmartAssistant

async def demo():
    """데모 실행"""
    print("🚀 Smart Assistant 데모")
    print("=" * 60)
    print("이 데모는 실제 이메일과 메신저 메시지를 수집하여")
    print("AI가 분석하고 TODO 리스트를 생성하는 과정을 보여줍니다.")
    print("=" * 60)
    
    # 설정
    email_config = {
        "email": "imyongjun@naver.com",
        "password": "X1BEZN9WTXPQ",  # 앱 비밀번호
        "provider": "naver"
    }
    
    messenger_config = {
        "use_simulator": True  # 시뮬레이터 사용
    }
    
    print(f"\n📧 이메일 설정: {email_config['email']}")
    print(f"📱 메신저: 시뮬레이터 모드")
    print(f"🤖 AI 모델: GPT-4o mini (API 키 없으면 기본 모드)")
    
    input(f"\n⏸️  시작하려면 Enter를 누르세요...")
    
    assistant = SmartAssistant()
    
    try:
        print(f"\n🔧 시스템 초기화 중...")
        await assistant.initialize(email_config, messenger_config)
        print(f"✅ 초기화 완료")
        
        print(f"\n📥 메시지 수집 중...")
        messages = await assistant.collect_messages(email_limit=5, messenger_limit=5)
        print(f"✅ {len(messages)}개 메시지 수집 완료")
        
        if not messages:
            print("❌ 수집된 메시지가 없습니다.")
            return
        
        # 수집된 메시지 미리보기
        print(f"\n📋 수집된 메시지 미리보기:")
        for i, msg in enumerate(messages[:3], 1):
            platform = msg.get('platform', 'unknown')
            sender = msg.get('sender', 'Unknown')
            subject = msg.get('subject', '')
            content = msg.get('content', '')[:100]
            
            print(f"{i}. [{platform.upper()}] {sender}")
            if subject:
                print(f"   제목: {subject}")
            print(f"   내용: {content}...")
            print()
        
        print(f"\n🔍 AI 분석 중...")
        print(f"   📝 메시지 요약")
        print(f"   🎯 우선순위 분류")
        print(f"   ⚡ 액션 추출")
        
        analysis_results = await assistant.analyze_messages()
        print(f"✅ {len(analysis_results)}개 메시지 분석 완료")
        
        print(f"\n📋 TODO 리스트 생성 중...")
        todo_list = await assistant.generate_todo_list(analysis_results)
        print(f"✅ TODO 리스트 생성 완료")
        
        # 결과 출력
        print(f"\n" + "=" * 60)
        print(f"📊 최종 결과")
        print(f"=" * 60)
        
        print(f"📈 통계:")
        print(f"   총 메시지: {todo_list['summary']['total_messages']}개")
        print(f"   추출된 액션: {todo_list['summary']['total_actions']}개")
        print(f"   TODO 아이템: {todo_list['total_items']}개")
        print(f"   긴급 아이템: {todo_list['summary']['urgent_items']}개")
        print(f"   데드라인 아이템: {todo_list['summary']['deadline_items']}개")
        
        print(f"\n🎯 우선순위 분포:")
        stats = todo_list['priority_stats']
        print(f"   🔴 High: {stats['high']}개")
        print(f"   🟡 Medium: {stats['medium']}개")
        print(f"   🟢 Low: {stats['low']}개")
        
        print(f"\n🔥 상위 TODO 아이템:")
        for i, item in enumerate(todo_list["items"][:10], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            icon = priority_icon.get(item['priority'], "⚪")
            
            print(f"{i:2d}. {icon} [{item['priority'].upper():5s}] {item['title']}")
            print(f"     👤 요청자: {item['requester']}")
            print(f"     📱 소스: {item['source_message']['platform']}")
            if item['deadline']:
                print(f"     ⏰ 데드라인: {item['deadline']}")
            print(f"     🏷️  타입: {item['type']}")
            print()
        
        # 결과 저장
        print(f"💾 결과 저장 중...")
        filename = f"demo_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        result_data = {
            "demo_info": {
                "timestamp": datetime.now().isoformat(),
                "total_messages": len(messages),
                "total_todos": todo_list['total_items']
            },
            "todo_list": todo_list,
            "messages": messages[:10],  # 처음 10개만 저장
            "analysis_results": analysis_results[:10]  # 처음 10개만 저장
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 결과가 {filename}에 저장되었습니다.")
        
        print(f"\n" + "=" * 60)
        print(f"🎉 데모 완료!")
        print(f"=" * 60)
        print(f"이제 Smart Assistant가 어떻게 작동하는지 확인했습니다.")
        print(f"실제 사용 시에는 다음과 같이 활용할 수 있습니다:")
        print(f"  1. 정기적인 이메일/메신저 모니터링")
        print(f"  2. 자동 TODO 리스트 생성")
        print(f"  3. 우선순위별 업무 관리")
        print(f"  4. AI 기반 메시지 분석")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"\n❌ 데모 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await assistant.cleanup()
        print(f"\n👋 데모를 종료합니다.")

if __name__ == "__main__":
    asyncio.run(demo())
