# -*- coding: utf-8 -*-
"""
간단한 테스트 스크립트
"""
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

print("🚀 Smart Assistant 간단 테스트")
print("=" * 50)

try:
    # 메신저 어댑터 테스트
    print("📱 메신저 어댑터 테스트...")
    from ingestors.messenger_adapter import MessengerAdapter
    
    messenger_config = {"use_simulator": True}
    adapter = MessengerAdapter(messenger_config)
    
    import asyncio
    async def test_messenger():
        messages = await adapter.get_all_unread_messages(5)
        print(f"✅ {len(messages)}개 메신저 메시지 수집 성공")
        for i, msg in enumerate(messages[:3], 1):
            print(f"  {i}. {msg.platform}: {msg.content[:50]}...")
        return messages
    
    messages = asyncio.run(test_messenger())
    
    # NLP 모듈 테스트
    print("\n🤖 NLP 모듈 테스트...")
    from nlp.summarize import MessageSummarizer
    from nlp.priority_ranker import PriorityRanker
    from nlp.action_extractor import ActionExtractor
    
    summarizer = MessageSummarizer()
    ranker = PriorityRanker()
    extractor = ActionExtractor()
    
    async def test_nlp():
        # 메시지를 딕셔너리 형태로 변환
        message_data = [{
            "msg_id": msg.msg_id,
            "sender": msg.sender,
            "subject": "",
            "body": msg.content,
            "content": msg.content,
            "date": msg.timestamp.isoformat()
        } for msg in messages[:2]]
        
        # 요약 테스트
        print("📝 메시지 요약 중...")
        summaries = await summarizer.batch_summarize(message_data)
        print(f"✅ {len(summaries)}개 메시지 요약 완료")
        
        # 우선순위 분류 테스트
        print("🎯 우선순위 분류 중...")
        ranked = await ranker.rank_messages(message_data)
        print(f"✅ {len(ranked)}개 메시지 분류 완료")
        
        # 액션 추출 테스트
        print("⚡ 액션 추출 중...")
        actions = await extractor.batch_extract_actions(message_data)
        print(f"✅ {len(actions)}개 액션 추출 완료")
        
        return summaries, ranked, actions
    
    summaries, ranked, actions = asyncio.run(test_nlp())
    
    # 결과 출력
    print("\n📊 테스트 결과:")
    print(f"  메신저 메시지: {len(messages)}개")
    print(f"  요약: {len(summaries)}개")
    print(f"  분류: {len(ranked)}개")
    print(f"  액션: {len(actions)}개")
    
    if ranked:
        print(f"\n🔥 우선순위 분류 결과:")
        for i, (msg, priority) in enumerate(ranked[:3], 1):
            print(f"  {i}. [{priority.priority_level.upper()}] {msg['sender']}: {msg['content'][:50]}...")
    
    if actions:
        print(f"\n⚡ 추출된 액션:")
        for i, action in enumerate(actions[:3], 1):
            print(f"  {i}. {action.action_type}: {action.title}")
    
    print(f"\n✅ 모든 테스트 완료!")
    
except Exception as e:
    print(f"❌ 테스트 오류: {e}")
    import traceback
    traceback.print_exc()
