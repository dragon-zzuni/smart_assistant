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

from datetime import datetime, timezone, timedelta
from data.messenger.importer import iter_messenger_messages  # 경로 그대로 쓰세요(상대 임포트)

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



def _to_aware_iso(ts: str | None) -> str:
    """문자열 타임스탬프를 UTC aware ISO8601로 표준화."""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    s = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)  # tz 포함/미포함 모두 허용
    except Exception:
        # YYYY-MM-DD HH:MM:SS 같은 포맷 처리
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    if dt.tzinfo is None:
        # naive면 UTC로 간주
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # 타임존 있으면 UTC로 변환
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()

def _sort_key(msg: dict) -> datetime:
    """날짜 키를 UTC aware datetime으로 반환(정렬용)."""
    try:
        return datetime.fromisoformat(msg["date"])
    except Exception:
        try:
            return datetime.fromisoformat(_to_aware_iso(msg.get("date")))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

# 로깅 설정 (간단하게)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def coalesce_messages(msgs, window_seconds=90, max_chars=1200):
    out = []
    last = None
    for m in sorted(msgs, key=lambda x: x["date"]):
        if last and (m["platform"] == last["platform"]
                     and m["sender"] == last["sender"]
                     and abs(datetime.fromisoformat(m["date"]) - datetime.fromisoformat(last["date"])) <= timedelta(seconds=window_seconds)):
            # 합치기
            merged = last["content"] + "\n" + (m["content"] or "")
            if len(merged) > max_chars:
                merged = merged[:max_chars] + " ..."
            last["content"] = merged
            last["body"]    = merged
            last["msg_id"] += f"+{m['msg_id']}"
            last["date"]     = m["date"]  # 최신으로
        else:
            mm = dict(m)
            text = mm.get("content") or ""
            if len(text) > max_chars:
                text = text[:max_chars] + " ..."
                mm["content"] = text
                mm["body"]    = text
            out.append(mm)
            last = mm
    return out

def _trim(s: str, n: int) -> str:
    if not s:
        return ""
    s = s.strip()
    return s if len(s) <= n else s[:n] + " ..."

async def build_overall_analysis_text(self, analysis_results: list, max_chars_total: int = 8000) -> str:
    """
    분석 탭에 뿌릴 통합 텍스트 생성:
      - 전체 메시지(제목/내용) 묶어 1회 요약
      - High / Medium / Low 섹션과 구분선
    """
    # 1) 전체 메시지에서 제목/내용 취합
    buffet = []
    acc = 0
    for r in analysis_results:
        msg = r["message"]
        sender = msg.get("sender") or ""
        subj = (msg.get("subject") or msg.get("content") or msg.get("body") or "").strip()
        line = f"{sender}: {subj}"
        if acc + len(line) > max_chars_total:
            break
        buffet.append(line); acc += len(line) + 1
    big_text = "\n".join(buffet)

    # 2) 1회 요약
    ov = await self.summarizer.summarize_message(big_text, sender="multi", subject="전체 메시지 요약")
    overview = ov.summary if hasattr(ov, "summary") else str(ov)

    # 3) 우선순위 섹션
    lines = []
    lines.append("📊 분석 결과 (통합)")
    lines.append("=" * 60)
    lines.append(overview)
    lines.append("")

    buckets = {"high": [], "medium": [], "low": []}
    for r in analysis_results:
        pr = r["priority"]
        level = (pr.get("priority_level") if isinstance(pr, dict) else getattr(pr, "priority_level", "low")).lower()
        buckets.setdefault(level, []).append(r)

    def push_bucket(name, items):
        lines.append(f"\n--- [{name.upper()}] {'-'*42}")
        for r in items[:8]:
            msg = r["message"]
            ttl = (msg.get("subject") or msg.get("content") or "")[:80]
            if len(ttl) >= 80: ttl += "..."
            sum_obj = r.get("summary")
            sum_txt = (sum_obj.get("summary") if isinstance(sum_obj, dict) else getattr(sum_obj, "summary", ""))[:100]
            lines.append(f"• {msg.get('sender','')} / {ttl}")
            if sum_txt:
                lines.append(f"  요약: {sum_txt}")
            if r.get("actions"):
                lines.append(f"  액션: {len(r['actions'])}개")

    push_bucket("high", buckets.get("high", []))
    push_bucket("medium", buckets.get("medium", []))
    push_bucket("low", buckets.get("low", []))

    return "\n".join(lines)



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

        self.analysis_report_text = ""     # 분석 결과 탭에 뿌릴 통합 리포트 문자열
        self.conversation_summary = None   # 대화 단위 요약(딕셔너리)   

    
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

        
    async def collect_messages(self,
                            email_limit: int = 30,
                            messenger_limit: int = 20,
                            json_limit: int = 100,
                            rooms=None,
                            include_system: bool = False,
                            overall_limit: int | None = None):
        """여러 소스에서 메시지 수집 후 공통 포맷으로 반환"""
        logger.info("📥 메시지 수집 시작...")
        all_messages = []
            

        # 1) 이메일 (기존)
        if self.email_collector:
            try:
                if await self.email_collector.connect():
                    emails = await self.email_collector.get_unread_emails(email_limit)
                    for email in emails:
                        all_messages.append({
                            "msg_id": email.msg_id,
                            "sender": email.sender,
                            "subject": email.subject,
                            "body": email.body,
                            "content": email.body,
                            "date": _to_aware_iso(email.date.isoformat()),
                            "type": "email",
                            "platform": "email",
                        })
                    logger.info(f"📧 {len(emails)}개의 이메일 수집")
                else:
                    logger.warning("이메일 연결 실패")
            except Exception as e:
                logger.error(f"이메일 수집 오류: {e}")

        # 2) 메신저 어댑터 (기존)
        if self.messenger_adapter:
            try:
                messages = await self.messenger_adapter.get_all_unread_messages(messenger_limit)
                for msg in messages:
                    all_messages.append({
                        "msg_id": msg.msg_id,
                        "sender": msg.sender,
                        "subject": "",
                        "body": msg.content,
                        "content": msg.content,
                        "date": _to_aware_iso(msg.timestamp.isoformat()),
                        "type": "messenger",
                        "platform": msg.platform,
                    })
                logger.info(f"📱 {len(messages)}개의 메신저 메시지 수집")
            except Exception as e:
                logger.error(f"메신저 수집 오류: {e}")

        # 3) data/messenger/*.json (신규)
        try:
            mlogs = iter_messenger_messages(
                root="data/messenger",
                rooms=rooms,
                include_system=include_system,
                limit=json_limit
            )
            count_json = 0
            for i, m in enumerate(mlogs):
                iso = _to_aware_iso(getattr(m, "timestamp", None))
                all_messages.append({
                    "msg_id": f"json_{iso}_{i}",
                    "sender": getattr(m, "username", None) or "unknown",
                    "subject": "",
                    "body": getattr(m, "message", None) or "",
                    "content": getattr(m, "message", None) or "",
                    "date": iso,
                    "type": "messenger",                 # 파이프라인 일관성 위해 messenger로 통일
                    "platform": getattr(m, "room", None) or "json",
                })
                count_json += 1
            logger.info(f"🗂️ JSON 로드: {count_json}개")
        except Exception as e:
            logger.error(f"JSON 메시지 로드 오류: {e}")

        # 4) 최신순 정렬 → 전체 상한
        all_messages = coalesce_messages(all_messages, window_seconds=90, max_chars=1200)
        all_messages.sort(key=_sort_key, reverse=True)

        if overall_limit:
            all_messages = all_messages[:overall_limit]

        self.collected_messages = all_messages
        logger.info(f"📥 총 {len(all_messages)}개 메시지 수집 완료")
        return all_messages
    # main.py (핵심 흐름 정리 예시)

    async def analyze_messages(self):
        if not self.collected_messages:
            logger.warning("분석할 메시지가 없습니다.")
            return []

        logger.info("🔍 메시지 분석 시작...")

        # 1) 우선순위 분류
        logger.info("🎯 우선순위 분류 중...")
        self.ranked_messages = await self.priority_ranker.rank_messages(self.collected_messages)

        TOP_N = 60
        top_msgs = [m for (m, _) in self.ranked_messages][:TOP_N]

        # 2) 상위 N개 요약
        logger.info(f"📝 상위 {TOP_N}개 메시지 요약 중...")
        self.summaries = await self.summarizer.batch_summarize(top_msgs)

        # msg_id → summary 맵
        summary_by_id = {}
        for m, s in zip(top_msgs, self.summaries):
            if s and not getattr(s, "original_id", None):
                s.original_id = m.get("msg_id")
            summary_by_id[m["msg_id"]] = s

        # 3) 액션 추출
        logger.info("⚡ 액션 추출 중...")
        actions = await self.action_extractor.batch_extract_actions(top_msgs)
        self.extracted_actions = actions

        actions_by_id = {}
        for a in actions:
            src = getattr(a, "source_message_id", None) or (a.get("source_message_id") if isinstance(a, dict) else None)
            if not src:
                continue
            actions_by_id.setdefault(src, []).append(a)

        # 4) 결과 병합 (전체 랭킹 순서 보존)
        results = []
        for message, priority in self.ranked_messages:
            mid = message["msg_id"]
            s   = summary_by_id.get(mid)
            pr  = priority.to_dict() if hasattr(priority, "to_dict") else priority
            acts = [x.to_dict() if hasattr(x, "to_dict") else x for x in actions_by_id.get(mid, [])]
            results.append({
                "message": message,
                "summary": (s.to_dict() if hasattr(s, "to_dict") else (s.__dict__ if s else None)),
                "priority": pr,
                "actions": acts,
                "analysis_timestamp": datetime.now().isoformat()
            })

        # 5) (선택) 메신저 대화 전체 요약을 프리앰블로 생성
        conv_text = ""
        try:
            chat_msgs = [m for m in self.collected_messages if m.get("type") == "messenger"]
            if chat_msgs:
                conv = await self.summarizer.summarize_conversation(chat_msgs)

                def _bullets(title, items, limit=6):
                    if not items:
                        return []
                    if isinstance(items, list):
                        items = items[:limit]
                    lines = [f"■ {title}"]
                    for it in items:
                        lines.append(f"- {it}")
                    lines.append("")
                    return lines

                parts = []
                if isinstance(conv, dict):
                    if conv.get("summary"):
                        parts += ["■ 대화 흐름 요약", "═"*60, conv["summary"].strip(), ""]
                    parts += _bullets("핵심 포인트", conv.get("key_points"))
                    parts += _bullets("결정 사항", conv.get("decisions"))
                    parts += _bullets("미해결/후속 필요", conv.get("unresolved"))
                    parts += _bullets("리스크/주의", conv.get("risks"))

                    # 액션아이템이 dict 리스트일 수도 있음
                    ai = conv.get("action_items") or []
                    if ai:
                        parts.append("■ 액션 아이템")
                        for a in ai[:8]:
                            if isinstance(a, dict):
                                title = a.get("title") or a.get("task") or str(a)
                                pr    = a.get("priority")
                                owner = a.get("owner")
                                due   = a.get("due")
                                meta = ", ".join([x for x in [
                                    f"우선:{pr}" if pr else None,
                                    f"담당:{owner}" if owner else None,
                                    f"마감:{due}" if due else None
                                ] if x])
                                parts.append(f"- {title}" + (f" ({meta})" if meta else ""))
                            else:
                                parts.append(f"- {a}")
                        parts.append("")

                    if conv.get("participants"):
                        parts += ["참여자: " + ", ".join(conv["participants"]), ""]

                # 혹시 문자열이 오면 그대로 사용
                if not parts and isinstance(conv, str):
                    parts = ["■ 대화 흐름 요약", "═"*60, conv.strip()]

                conv_text = "\n".join(parts).strip()
        except Exception as e:
            logger.warning(f"대화 요약 실패: {e}")


        # 6) 분석 결과 탭 텍스트 생성 (우선순위 섹션 포함)
        sections_text = await build_overall_analysis_text(self, results)
        self.analysis_report_text = sections_text + ("\n\n" + conv_text if conv_text else "")


        logger.info(f"🔍 {len(results)}개 메시지 분석 완료")
        return results

    
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
