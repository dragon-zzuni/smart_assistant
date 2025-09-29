# -*- coding: utf-8 -*-
"""
메시지 요약 모듈 - LLM을 사용하여 이메일/메신저 메시지 요약
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from openai import AsyncOpenAI
except Exception:
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
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or LLM_CONFIG.get("openai_api_key")
        self.model = LLM_CONFIG.get("model", "gpt-4o-mini")
        self.max_tokens = LLM_CONFIG.get("max_tokens", 1000)
        self.temperature = LLM_CONFIG.get("temperature", 0.3)
        
        if AsyncOpenAI and self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.is_available = True
        else:
            self.is_available = False
            logger.warning("OpenAI API 키가 설정되지 않았습니다. 기본 요약 모드로 동작합니다.")

    async def summarize_message(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        """메시지 요약"""
        if self.is_available:
            return await self._llm_summarize(content, sender, subject)
        else:
            return self._basic_summarize(content, sender, subject)
    
    async def _llm_summarize(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        """LLM을 사용한 고급 요약"""
        try:
            prompt = self._create_summarization_prompt(content, sender, subject)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 업무용 메시지 분석 전문가입니다. 이메일과 메신저 메시지를 분석하여 요약, 핵심 포인트, 감정, 긴급도, 필요한 액션을 파악합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            result_text = response.choices[0].message.content
            return self._parse_llm_response(result_text, sender)
            
        except Exception as e:
            logger.error(f"LLM 요약 오류: {e}")
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
    
    def _parse_llm_response(self, response_text: str, sender: str) -> MessageSummary:
        """LLM 응답 파싱"""
        try:
            # JSON 추출
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
        """여러 메시지 일괄 요약"""
        summaries = []
        
        for msg in messages:
            try:
                content = msg.get("body", "") or msg.get("content", "")
                sender = msg.get("sender", "")
                subject = msg.get("subject", "")
                
                summary = await self.summarize_message(content, sender, subject)
                summaries.append(summary)
                
            except Exception as e:
                logger.error(f"메시지 요약 오류: {e}")
                continue
        
        logger.info(f"📝 {len(summaries)}개 메시지 요약 완료")
        return summaries
    
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
