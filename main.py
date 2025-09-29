# -*- coding: utf-8 -*-
"""
Smart Assistant 메인 애플리케이션
이메일과 메신저 메시지를 수집하고, LLM으로 분석하여 TODO 리스트를 생성하는 시스템
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# # Windows 한글 출력 설정
# import sys
# if hasattr(sys.stdout, "reconfigure"):  # Python 3.7+
#     sys.stdout.reconfigure(encoding="utf-8")
#     sys.stderr.reconfigure(encoding="utf-8")
# # 아니면 아예 아무 것도 안 해도 됨


from config.settings import LOGGING_CONFIG
from ingestors.email_imap import EmailIMAPCollector, EmailMessage
from ingestors.messenger_adapter import MessengerAdapter, Message
from nlp.summarize import MessageSummarizer
from nlp.priority_ranker import PriorityRanker
from nlp.action_extractor import ActionExtractor
from config.settings import LLM_CONFIG

# 로깅 설정 (간단하게)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartAssistant:
    """스마트 어시스턴트 메인 클래스"""
    
    def __init__(self):
        self.email_collector = None
        self.messenger_adapter = None
        self.summarizer = MessageSummarizer()
        self.priority_ranker = PriorityRanker()
        self.action_extractor = ActionExtractor()
        
        self.collected_messages = []
        self.summaries = []
        self.ranked_messages = []
        self.extracted_actions = []
    
    async def initialize(self, email_config: Dict = None, messenger_config: Dict = None):
        """시스템 초기화"""
        logger.info("🚀 Smart Assistant 초기화 중...")
        
        # 이메일 수집기 초기화
        if email_config:
            self.email_collector = EmailIMAPCollector(
                email_config["email"],
                email_config["password"],
                email_config.get("provider", "naver")
            )
            logger.info("📧 이메일 수집기 초기화 완료")
        
        # 메신저 어댑터 초기화
        if messenger_config:
            self.messenger_adapter = MessengerAdapter(messenger_config)
            logger.info("📱 메신저 어댑터 초기화 완료")
        
        logger.info("✅ 초기화 완료")
    
    async def collect_messages(self, email_limit: int = 150, messenger_limit: int = 10000) -> List[Dict]:
        """메시지 수집"""
        logger.info("📥 메시지 수집 시작...")
        
        all_messages = []
        
        # 이메일 수집
        if self.email_collector:
            try:
                if await self.email_collector.connect():
                    emails = await self.email_collector.get_unread_emails(email_limit)
                    for email in emails:
                        message_data = {
                            "msg_id": email.msg_id,
                            "sender": email.sender,
                            "subject": email.subject,
                            "body": email.body,
                            "content": email.body,  # 메신저 호환성
                            "date": email.date.isoformat(),
                            "type": "email",
                            "platform": "email"
                        }
                        all_messages.append(message_data)
                    
                    logger.info(f"📧 {len(emails)}개의 이메일 수집")
                else:
                    logger.warning("이메일 연결 실패")
            except Exception as e:
                logger.error(f"이메일 수집 오류: {e}")
        
        # 메신저 메시지 수집
        if self.messenger_adapter:
            try:
                messages = await self.messenger_adapter.get_all_unread_messages(messenger_limit)
                for msg in messages:
                    message_data = {
                        "msg_id": msg.msg_id,
                        "sender": msg.sender,
                        "subject": "",  # 메신저는 제목이 없을 수 있음
                        "body": msg.content,
                        "content": msg.content,
                        "date": msg.timestamp.isoformat(),
                        "type": "messenger",
                        "platform": msg.platform
                    }
                    all_messages.append(message_data)
                
                logger.info(f"📱 {len(messages)}개의 메신저 메시지 수집")
            except Exception as e:
                logger.error(f"메신저 수집 오류: {e}")
        
        self.collected_messages = all_messages
        logger.info(f"📥 총 {len(all_messages)}개 메시지 수집 완료")
        return all_messages
    
    async def analyze_messages(self) -> List[Dict]:
        """메시지 분석 (요약, 우선순위 분류, 액션 추출)"""
        if not self.collected_messages:
            logger.warning("분석할 메시지가 없습니다.")
            return []
        
        logger.info("🔍 메시지 분석 시작...")
        
        # 1. 메시지 요약
        logger.info("📝 메시지 요약 중...")
        self.summaries = await self.summarizer.batch_summarize(self.collected_messages)
        
        # 2. 우선순위 분류
        logger.info("🎯 우선순위 분류 중...")
        self.ranked_messages = await self.priority_ranker.rank_messages(self.collected_messages)
        
        # 3. 액션 추출
        logger.info("⚡ 액션 추출 중...")
        self.extracted_actions = await self.action_extractor.batch_extract_actions(self.collected_messages)
        
        # 결과 통합
        analysis_results = []
        for message, priority_score in self.ranked_messages:
            # 해당 메시지의 요약 찾기
            summary = next(
                (s for s in self.summaries if s.original_id == message["msg_id"]), 
                None
            )
            
            # 해당 메시지의 액션들 찾기
            message_actions = [
                action for action in self.extracted_actions 
                if action.source_message_id == message["msg_id"]
            ]
            
            result = {
                "message": message,
                "summary": summary.to_dict() if summary else None,
                "priority": priority_score.to_dict(),
                "actions": [action.to_dict() for action in message_actions],
                "analysis_timestamp": datetime.now().isoformat()
            }
            analysis_results.append(result)
        
        logger.info(f"🔍 {len(analysis_results)}개 메시지 분석 완료")
        return analysis_results
    
    async def generate_todo_list(self, analysis_results: List[Dict]) -> Dict:
        """TODO 리스트 생성"""
        logger.info("📋 TODO 리스트 생성 중...")
        
        todo_items = []
        high_priority_count = 0
        medium_priority_count = 0
        low_priority_count = 0
        
        for result in analysis_results:
            priority_level = result["priority"]["priority_level"]
            
            # 우선순위별 카운트
            if priority_level == "high":
                high_priority_count += 1
            elif priority_level == "medium":
                medium_priority_count += 1
            else:
                low_priority_count += 1
            
            # 액션들을 TODO 아이템으로 변환
            for action in result["actions"]:
                todo_item = {
                    "id": action["action_id"],
                    "title": action["title"],
                    "description": action["description"],
                    "priority": action["priority"],
                    "deadline": action["deadline"],
                    "requester": action["requester"],
                    "type": action["action_type"],
                    "status": "pending",
                    "source_message": {
                        "id": result["message"]["msg_id"],
                        "sender": result["message"]["sender"],
                        "subject": result["message"]["subject"],
                        "platform": result["message"]["platform"]
                    },
                    "created_at": action["created_at"]
                }
                todo_items.append(todo_item)
        
        # 우선순위별로 정렬
        priority_order = {"high": 3, "medium": 2, "low": 1}
        todo_items.sort(
            key=lambda x: (priority_order.get(x["priority"], 1), x["deadline"] or "9999-12-31"),
            reverse=True
        )
        
        todo_list = {
            "generated_at": datetime.now().isoformat(),
            "total_items": len(todo_items),
            "priority_stats": {
                "high": high_priority_count,
                "medium": medium_priority_count,
                "low": low_priority_count
            },
            "items": todo_items[:20],  # 상위 20개만
            "summary": {
                "total_messages": len(analysis_results),
                "total_actions": len(self.extracted_actions),
                "urgent_items": len([item for item in todo_items if item["priority"] == "high"]),
                "deadline_items": len([item for item in todo_items if item["deadline"]])
            }
        }
        
        logger.info(f"📋 TODO 리스트 생성 완료: {len(todo_items)}개 아이템")
        return todo_list
    
    async def cleanup(self):
        """리소스 정리"""
        logger.info("🧹 리소스 정리 중...")
        
        if self.email_collector:
            await self.email_collector.disconnect()
        
        logger.info("✅ 정리 완료")
    
    async def run_full_cycle(self, email_config: Dict = None, messenger_config: Dict = None) -> Dict:
        """전체 사이클 실행"""
        try:
            # 1. 초기화
            await self.initialize(email_config, messenger_config)
            
            # 2. 메시지 수집
            messages = await self.collect_messages()
            
            if not messages:
                return {"error": "수집된 메시지가 없습니다."}
            
            # 3. 메시지 분석
            analysis_results = await self.analyze_messages()
            
            # 4. TODO 리스트 생성
            todo_list = await self.generate_todo_list(analysis_results)
            
            return {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "collected_messages": len(messages)
            }
            
        except Exception as e:
            logger.error(f"전체 사이클 실행 오류: {e}")
            return {"error": str(e)}
        
        finally:
            await self.cleanup()


# 테스트 함수
async def test_smart_assistant():
    """스마트 어시스턴트 테스트"""
    print("🚀 Smart Assistant 테스트 시작")
    
    # 테스트 설정 (실제 사용 시 환경변수에서 가져오기)
    email_config = {
        "email": "imyongjun@naver.com",
        "password": "X1BEZN9WTXPQ",  # 앱 비밀번호
        "provider": "naver"
    }
    
    messenger_config = {
        "use_simulator": True  # 시뮬레이터 사용
    }
    
    assistant = SmartAssistant()
    
    try:
        result = await assistant.run_full_cycle(email_config, messenger_config)
        
        if result.get("success"):
            todo_list = result["todo_list"]
            
            print(f"\n📋 TODO 리스트 생성 완료!")
            print(f"총 {todo_list['total_items']}개 아이템")
            print(f"우선순위: High({todo_list['priority_stats']['high']}), Medium({todo_list['priority_stats']['medium']}), Low({todo_list['priority_stats']['low']})")
            
            print(f"\n🔥 상위 5개 TODO:")
            for i, item in enumerate(todo_list["items"][:5], 1):
                print(f"{i}. [{item['priority'].upper()}] {item['title']}")
                print(f"   요청자: {item['requester']}")
                if item['deadline']:
                    print(f"   데드라인: {item['deadline']}")
                print(f"   타입: {item['type']}")
                print()
        else:
            print(f"❌ 오류: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")


if __name__ == "__main__":
    # 간단한 테스트 실행
    print("Smart Assistant v1.0")
    print("=" * 50)
    
    # 환경변수 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   LLM 기능은 기본 모드로 동작합니다.")
    
    asyncio.run(test_smart_assistant())
