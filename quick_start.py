# -*- coding: utf-8 -*-
"""
Quick Start - Smart Assistant 빠른 시작
"""
import sys
import os
import asyncio

# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

async def main():
    print("🚀 Smart Assistant 빠른 시작")
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
        
        print(f"\n🔥 상위 TODO 아이템:")
        for i, action in enumerate(actions[:5], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            icon = priority_icon.get(action.priority, "⚪")
            print(f"{i}. {icon} {action.title}")
            print(f"   요청자: {action.requester}")
            if action.deadline:
                print(f"   데드라인: {action.deadline}")
            print()
        
        print(f"✅ Smart Assistant 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
