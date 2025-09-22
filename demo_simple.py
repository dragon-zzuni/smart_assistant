# -*- coding: utf-8 -*-
"""
Smart Assistant 간단 데모
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

async def demo():
    """간단 데모"""
    print("🚀 Smart Assistant 데모")
    print("=" * 50)
    
    try:
        # 메신저 시뮬레이터 테스트
        print("📱 메신저 메시지 수집...")
        from ingestors.messenger_adapter import MessengerAdapter
        
        messenger_config = {"use_simulator": True}
        adapter = MessengerAdapter(messenger_config)
        messages = await adapter.get_all_unread_messages(5)
        
        print(f"✅ {len(messages)}개 메신저 메시지 수집")
        
        # 메시지를 딕셔너리로 변환
        message_data = []
        for msg in messages:
            message_data.append({
                "msg_id": msg.msg_id,
                "sender": msg.sender,
                "subject": "",
                "body": msg.content,
                "content": msg.content,
                "date": msg.timestamp.isoformat(),
                "type": "messenger",
                "platform": msg.platform
            })
        
        # NLP 분석
        print("🤖 AI 분석 중...")
        
        # 요약
        from nlp.summarize import MessageSummarizer
        summarizer = MessageSummarizer()
        summaries = await summarizer.batch_summarize(message_data)
        print(f"✅ {len(summaries)}개 메시지 요약 완료")
        
        # 우선순위 분류
        from nlp.priority_ranker import PriorityRanker
        ranker = PriorityRanker()
        ranked = await ranker.rank_messages(message_data)
        print(f"✅ {len(ranked)}개 메시지 분류 완료")
        
        # 액션 추출
        from nlp.action_extractor import ActionExtractor
        extractor = ActionExtractor()
        actions = await extractor.batch_extract_actions(message_data)
        print(f"✅ {len(actions)}개 액션 추출 완료")
        
        # 결과 출력
        print(f"\n📊 분석 결과:")
        print(f"   메시지: {len(message_data)}개")
        print(f"   요약: {len(summaries)}개")
        print(f"   분류: {len(ranked)}개")
        print(f"   액션: {len(actions)}개")
        
        print(f"\n🔥 우선순위별 메시지:")
        for i, (msg, priority) in enumerate(ranked[:5], 1):
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            priority_icon = icon.get(priority.priority_level, "⚪")
            print(f"{i}. {priority_icon} [{priority.priority_level.upper()}] {msg['sender']}")
            print(f"   내용: {msg['content'][:80]}...")
            print(f"   점수: {priority.overall_score:.2f}")
            print()
        
        print(f"\n⚡ 추출된 액션:")
        for i, action in enumerate(actions[:5], 1):
            print(f"{i}. {action.action_type}: {action.title}")
            print(f"   요청자: {action.requester}")
            if action.deadline:
                print(f"   데드라인: {action.deadline}")
            print(f"   우선순위: {action.priority}")
            print()
        
        # TODO 리스트 생성
        print(f"\n📋 TODO 리스트:")
        todo_items = []
        for action in actions:
            todo_item = {
                "title": action.title,
                "priority": action.priority,
                "requester": action.requester,
                "deadline": action.deadline.isoformat() if action.deadline else None,
                "type": action.action_type
            }
            todo_items.append(todo_item)
        
        # 우선순위별로 정렬
        priority_order = {"high": 3, "medium": 2, "low": 1}
        todo_items.sort(key=lambda x: priority_order.get(x["priority"], 1), reverse=True)
        
        for i, item in enumerate(todo_items[:10], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            icon = priority_icon.get(item["priority"], "⚪")
            print(f"{i:2d}. {icon} {item['title']}")
            print(f"     요청자: {item['requester']} | 타입: {item['type']}")
            if item['deadline']:
                print(f"     데드라인: {item['deadline']}")
            print()
        
        # 결과 저장
        result = {
            "timestamp": datetime.now().isoformat(),
            "messages": message_data,
            "summaries": [s.to_dict() for s in summaries],
            "ranked_messages": [(msg, priority.to_dict()) for msg, priority in ranked],
            "actions": [action.to_dict() for action in actions],
            "todo_items": todo_items
        }
        
        filename = f"demo_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과가 {filename}에 저장되었습니다.")
        print(f"\n✅ 데모 완료!")
        
    except Exception as e:
        print(f"❌ 데모 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo())
