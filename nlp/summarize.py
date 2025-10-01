# -*- coding: utf-8 -*-
"""
메시지 요약 모듈 - LLM을 사용하여 이메일/메신저 메시지 요약
"""
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    # ✅ v1 클라이언트 (pip install openai>=1.0)
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from config.settings import LLM_CONFIG, PRIORITY_RULES

logger = logging.getLogger(__name__)






@dataclass
class MessageSummary:
    """메시지 요약 데이터 클래스"""
    original_id: str
    summary: str
    key_points: List[str]
    sentiment: str  # positive, negative, neutral
    urgency_level: str  # high, medium, low
    action_required: bool
    suggested_response: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "original_id": self.original_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "sentiment": self.sentiment,
            "urgency_level": self.urgency_level,
            "action_required": self.action_required,
            "suggested_response": self.suggested_response,
            "created_at": self.created_at.isoformat()
        }

class MessageSummarizer:
    """메시지 요약기"""
    
    def _build_transcript(self, messages: List[Dict], max_chars: int = 12000) -> str:
        """여러 메시지를 시간순으로 묶어 한 번에 요약할 수 있는 전개문 생성"""
        rows, total = [], 0

        def _ts(m):
            return (m.get("date") or m.get("timestamp") or m.get("datetime") or "")

        for m in sorted(messages, key=_ts):
            sender = (m.get("sender") or m.get("username") or "").strip()
            text   = (m.get("content") or m.get("body") or m.get("message") or "").strip()
            if not text:
                continue
            if (m.get("type") == "system") or (sender.lower() == "system"):
                continue

            line = f"{sender}: {text}"
            if total + len(line) > max_chars:
                break
            rows.append(line)
            total += len(line) + 1

        return "\n".join(rows)

    def _conversation_prompt(self, transcript: str) -> str:
        return f"""
    아래는 여러 사람이 주고받은 대화 전체입니다. 대화 흐름을 분석해 **순수 JSON만** 출력하세요.

    <대화>
    {transcript}

    JSON 스키마:
    {{
    "summary": "대화 전체 핵심 요약 (3~6문장)",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
    "decisions": ["확정된 결정 사항"],
    "unresolved": ["미해결/후속 필요 이슈"],
    "risks": ["리스크/주의사항"],
    "action_items": [
        {{"title":"해야 할 일", "priority":"High|Medium|Low", "owner":"선택", "due":"선택"}}
    ]
    }}
    """

    class ConversationSummary:
        def __init__(self, data: Dict):
            self.summary      = data.get("summary", "")
            self.key_points   = data.get("key_points", [])
            self.decisions    = data.get("decisions", [])
            self.unresolved   = data.get("unresolved", [])
            self.risks        = data.get("risks", [])
            self.action_items = data.get("action_items", [])

        def to_text(self) -> str:
            parts = []
            parts.append("■ 대화 흐름 요약")
            parts.append("="*60)
            parts.append(self.summary or "(요약 없음)")
            parts.append("")
            parts.append("■ 핵심 포인트")
            parts.append("- " + "\n- ".join(self.key_points or ["(없음)"]))
            parts.append("")
            if self.decisions:
                parts.append("■ 결정 사항")
                parts.append("- " + "\n- ".join(self.decisions))
                parts.append("")
            if self.unresolved:
                parts.append("■ 미해결/후속 필요")
                parts.append("- " + "\n- ".join(self.unresolved))
                parts.append("")
            if self.risks:
                parts.append("■ 리스크/주의")
                parts.append("- " + "\n- ".join(self.risks))
                parts.append("")
            if self.action_items:
                parts.append("■ 실행 항목(우선순위)")
                parts.append("="*60)
                for i,a in enumerate(self.action_items,1):
                    parts.append(f"{i}. [{a.get('priority','Low')}] {a.get('title','')}"
                                + (f" (담당:{a.get('owner')})" if a.get('owner') else "")
                                + (f" (기한:{a.get('due')})" if a.get('due') else ""))
            return "\n".join(parts)

    async def summarize_conversation(self, messages: List[Dict]) -> Dict:
        """대화 전체를 1회 호출로 요약하여 dict(JSON)으로 반환"""
        import json
        transcript = self._build_transcript(messages, max_chars=12000)
        if not transcript:
            return {"summary":"", "key_points":[], "decisions":[], "unresolved":[], "risks":[], "action_items":[]}

        prompt = self._conversation_prompt(transcript)

        extra = {}
        # OpenAI 계열에서 JSON 강제 포맷 필요할 때만
        if str(self.model).startswith("openai/"):
            extra["response_format"] = {"type": "json_object"}

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "당신은 회의/대화 요약 전문가입니다. 액션아이템을 명확히 뽑습니다."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            # ❌ usage 같은 요청 인자 넣지 마세요
            **extra,
        )

        text = (resp.choices[0].message.content or "").strip().strip("`")
        # JSON 부분만 추출
        s, e = text.find("{"), text.rfind("}") + 1
        try:
            return json.loads(text[s:e])
        except Exception:
            return {"summary": text, "key_points": [], "decisions": [], "unresolved": [], "risks": [], "action_items": []}

    def __init__(self, api_key: str = None):
        self.provider = LLM_CONFIG.get("provider", "openrouter")
        self.model = LLM_CONFIG.get("model", "openrouter/auto")
        self.max_tokens = LLM_CONFIG.get("max_tokens", 1000)
        self.temperature = LLM_CONFIG.get("temperature", 0.3)

        self.client = None
        self.is_available = False

        if AsyncOpenAI is None:
            logger.warning("openai 패키지가 설치되어 있지 않습니다. 기본 요약 모드로 동작합니다.")
            return

        if self.provider == "openrouter":
            key = api_key or LLM_CONFIG.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            base_url = LLM_CONFIG.get("openrouter_base_url", "https://openrouter.ai/api/v1")
            if key:
                # ✅ OpenRouter: base_url + API Key + (선택) 기본 헤더
                self.client = AsyncOpenAI(
                    api_key=key,
                    base_url=base_url,
                    default_headers={
                        # 아래 두 헤더는 권장(트래픽 출처 표시)
                        "HTTP-Referer": "https://github.com/dragon-zzuni/smart_assistant",
                        "X-Title": "smart_assistant",
                    },
                    timeout=30.0,
                )
                self.is_available = True
        else:
            # OpenAI 직접 사용시
            key = api_key or LLM_CONFIG.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if key:
                self.client = AsyncOpenAI(api_key=key)
                self.is_available = True

        if not self.is_available:
            logger.warning("LLM API 키가 설정되지 않았습니다. 기본 요약 모드로 동작합니다.")

    async def summarize_message(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        if self.is_available and self.client:
            return await self._llm_summarize(content, sender, subject)
        else:
            return self._basic_summarize(content, sender, subject)
    
    def _create_summarization_prompt(self, content: str, sender: str, subject: str) -> str:
        """요약 프롬프트 생성"""
        prompt = f"""
다음 메시지를 분석하여 JSON 형식으로 답변해주세요:

발신자: {sender}
제목: {subject}
내용: {content[:2000]}  # 내용이 길면 앞부분만

다음 형식으로 분석해주세요:
{{
    "summary": "메시지의 핵심 내용을 2-3문장으로 요약",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "sentiment": "positive/negative/neutral 중 하나",
    "urgency_level": "high/medium/low 중 하나",
    "action_required": true/false,
    "suggested_response": "권장 응답 내용 (선택사항)"
}}

분석 기준:
- urgency_level: 긴급 키워드(긴급, urgent, asap, 즉시, 오늘까지, deadline)가 있으면 high
- action_required: 구체적인 요청, 미팅, 보고서 제출 등이 있으면 true
- sentiment: 긍정적/부정적/중립적 톤 분석
"""
        return prompt

    async def _llm_summarize(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        """OpenRouter/OpenAI 공용 Chat Completions"""
        extra = {}
        if self.model.startswith("openai/"):
            extra["response_format"] = {"type": "json_object"}

        try:
            prompt = self._create_summarization_prompt(content, sender, subject)

            # ✅ v1 스타일
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 업무용 메시지 분석 전문가입니다. 이메일과 메신저 메시지를 분석하여 요약, 핵심 포인트, 감정, 긴급도, 필요한 액션을 파악합니다."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                **extra,
            )

            result_text = resp.choices[0].message.content
            return self._parse_llm_response(result_text, sender)

        except Exception as e:
            logger.error(f"LLM 요약 오류: {e}")
            return self._basic_summarize(content, sender, subject)
    
    def _parse_llm_response(self, response_text: str, sender: str) -> MessageSummary:
        """LLM 응답 파싱"""
        try:
            # JSON 추출
            response_text = (response_text or "").strip().strip("`")
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                return MessageSummary(
                    original_id=f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    summary=data.get("summary", ""),
                    key_points=data.get("key_points", []),
                    sentiment=data.get("sentiment", "neutral"),
                    urgency_level=data.get("urgency_level", "low"),
                    action_required=data.get("action_required", False),
                    suggested_response=data.get("suggested_response")
                )
        except Exception as e:
            logger.error(f"LLM 응답 파싱 오류: {e}")
        
        # 파싱 실패 시 기본 요약
        return self._basic_summarize(response_text, sender)
    
    def _basic_summarize(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        """기본 요약 (LLM 없이)"""
        # 간단한 키워드 기반 분석
        urgency_keywords = PRIORITY_RULES.get("high_priority_keywords", [])
        action_keywords = ["요청", "부탁", "미팅", "회의", "보고서", "제출", "검토", "확인"]
        
        content_lower = content.lower()
        
        # 긴급도 분석
        urgency_level = "low"
        for keyword in urgency_keywords:
            if keyword in content_lower:
                urgency_level = "high"
                break
        
        # 액션 필요성 분석
        action_required = any(keyword in content_lower for keyword in action_keywords)
        
        # 감정 분석 (간단한 키워드 기반)
        positive_words = ["감사", "좋", "잘", "성공", "완료", "수고"]
        negative_words = ["문제", "오류", "실패", "늦", "미완료", "불만"]
        
        sentiment = "neutral"
        if any(word in content_lower for word in positive_words):
            sentiment = "positive"
        elif any(word in content_lower for word in negative_words):
            sentiment = "negative"
        
        # 기본 요약 생성
        summary = content[:200] + "..." if len(content) > 200 else content
        
        # 핵심 포인트 추출 (간단한 문장 분할)
        sentences = content.split('.')[:3]
        key_points = [s.strip() for s in sentences if s.strip()]
        
        return MessageSummary(
            original_id=f"basic_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            summary=summary,
            key_points=key_points,
            sentiment=sentiment,
            urgency_level=urgency_level,
            action_required=action_required
        )
    
    async def batch_summarize(self, messages: List[Dict]) -> List[MessageSummary]:
        """여러 메시지를 동시(제한된 동시성)로 요약. 입력 순서를 보존합니다."""
        if not messages:
            return []

        # 동시 실행 상한 (리밋/속도 균형용)
        CONCURRENCY = 5
        sem = asyncio.Semaphore(CONCURRENCY)

        results: List[MessageSummary] = [None] * len(messages)  # 입력 순서 유지용

        async def one(i: int, m: Dict):
            content = (m.get("content") or m.get("body") or "").strip()
            sender  = (m.get("sender")  or "").strip()
            subject = (m.get("subject") or "").strip()

            # 내용이 비면 호출하지 않고 기본 요약
            if not content:
                s = self._basic_summarize(content, sender, subject)
                s.original_id = m.get("msg_id") or s.original_id   # ✅ 여기
                results[i] = s
                return


            try:
                async with sem:
                    s = await self.summarize_message(content, sender, subject)
                    # ✅ 요약 객체에 원본 메시지 ID 연결 (핵심)
                    s.original_id = m.get("msg_id") or s.original_id
                    results[i] = s
            except Exception as e:
                logger.error(f"메시지 요약 오류 (index={i}): {e}")
                s = self._basic_summarize(content, sender, subject)
                s.original_id = m.get("msg_id") or s.original_id   # ✅ 여기
                results[i] = s
                
        await asyncio.gather(*[asyncio.create_task(one(i, m)) for i, m in enumerate(messages)])

        logger.info(f"📝 {sum(1 for r in results if r is not None)}개 메시지 요약 완료")
        return results

    
    def _extract_deadlines(self, content: str) -> List[str]:
        """데드라인 추출"""
        import re
        
        deadline_patterns = [
            r"(\d{1,2}월\s*\d{1,2}일)",
            r"(\d{1,2}/\d{1,2})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(오늘까지|내일까지|이번 주까지|다음 주까지)",
            r"(월요일까지|화요일까지|수요일까지|목요일까지|금요일까지)"
        ]
        
        deadlines = []
        for pattern in deadline_patterns:
            matches = re.findall(pattern, content)
            deadlines.extend(matches)
        
        return deadlines
    
    def _extract_meeting_info(self, content: str) -> Dict:
        """미팅 정보 추출"""
        import re
        
        meeting_info = {}
        
        # 시간 패턴
        time_pattern = r"(\d{1,2}:\d{2}|\d{1,2}시|\d{1,2}월\s*\d{1,2}일\s*\d{1,2}시)"
        time_matches = re.findall(time_pattern, content)
        if time_matches:
            meeting_info["time"] = time_matches[0]
        
        # 장소 패턴
        location_pattern = r"(회의실|오피스|사무실|카페|식당|\d+층|\w+룸)"
        location_matches = re.findall(location_pattern, content)
        if location_matches:
            meeting_info["location"] = location_matches[0]
        
        return meeting_info


# 테스트 함수
async def test_summarizer():
    """요약기 테스트"""
    summarizer = MessageSummarizer()
    
    test_messages = [
        {
            "sender": "김과장",
            "subject": "긴급: 내일 오전 10시 팀 미팅",
            "body": "안녕하세요. 내일 오전 10시에 3층 회의실에서 팀 미팅이 있습니다. 프로젝트 진행 상황을 보고하고 다음 주 계획을 논의할 예정입니다. 준비해주세요.",
            "content": "안녕하세요. 내일 오전 10시에 3층 회의실에서 팀 미팅이 있습니다. 프로젝트 진행 상황을 보고하고 다음 주 계획을 논의할 예정입니다. 준비해주세요."
        },
        {
            "sender": "박대리",
            "subject": "프로젝트 문서 검토 요청",
            "body": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다.",
            "content": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다."
        }
    ]
    
    summaries = await summarizer.batch_summarize(test_messages)
    
    print(f"📝 {len(summaries)}개 메시지 요약 완료")
    for summary in summaries:
        print(f"\n- 요약: {summary.summary}")
        print(f"  긴급도: {summary.urgency_level}")
        print(f"  액션 필요: {summary.action_required}")
        print(f"  핵심 포인트: {', '.join(summary.key_points)}")


if __name__ == "__main__":
    asyncio.run(test_summarizer())
