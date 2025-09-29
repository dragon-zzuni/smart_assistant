# -*- coding: utf-8 -*-
"""
Messenger 어댑터 - 다양한 메신저 서비스에서 메시지 수집
현재는 시뮬레이터로 구현, 향후 실제 API 연동 가능
"""
import asyncio
import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from messenger_adapter.sqlite_adapter import SQLiteMessageStore
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class Message:
    """메신저 메시지 데이터 클래스"""
    msg_id: str
    sender: str
    recipient: str
    content: str
    timestamp: datetime
    platform: str
    is_read: bool = False
    priority: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "platform": self.platform,
            "is_read": self.is_read,
            "priority": self.priority
        }


class MessengerSimulator:
    """메신저 시뮬레이터 - 실제 API가 없을 때 사용"""
    
    def __init__(self, data_file: str = "sample_messages.json"):
        self.data_file = Path(data_file)
        self.messages = []
        self._load_sample_data()
    
    def _load_sample_data(self):
        """샘플 메시지 데이터 로드"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                logger.info(f"📱 {len(self.messages)}개의 샘플 메시지 로드")
            except Exception as e:
                logger.error(f"샘플 데이터 로드 오류: {e}")
                self._create_sample_data()
        else:
            self._create_sample_data()
    
    def _create_sample_data(self):
        """샘플 메시지 데이터 생성"""
        self.messages = [
            {
                "msg_id": "msg_001",
                "sender": "김과장",
                "recipient": "나",
                "content": "내일 오전 10시에 팀 미팅 있습니다. 준비해주세요.",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "platform": "slack",
                "is_read": False,
                "priority": "high"
            },
            {
                "msg_id": "msg_002",
                "sender": "박대리",
                "recipient": "나",
                "content": "프로젝트 문서 검토 부탁드립니다.",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "platform": "teams",
                "is_read": False,
                "priority": "medium"
            },
            {
                "msg_id": "msg_003",
                "sender": "이부장",
                "recipient": "나",
                "content": "월요일까지 보고서 제출 바랍니다.",
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "platform": "kakaowork",
                "is_read": False,
                "priority": "high"
            },
            {
                "msg_id": "msg_004",
                "sender": "최팀장",
                "recipient": "나",
                "content": "오늘 점심 같이 드실까요?",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "platform": "slack",
                "is_read": False,
                "priority": "low"
            },
            {
                "msg_id": "msg_005",
                "sender": "정대리",
                "recipient": "나",
                "content": "클라이언트 미팅 준비 자료 확인했습니다.",
                "timestamp": datetime.now().isoformat(),
                "platform": "teams",
                "is_read": False,
                "priority": "medium"
            }
        ]
        
        # 샘플 데이터 저장
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            logger.info("📱 샘플 메시지 데이터 생성 완료")
        except Exception as e:
            logger.error(f"샘플 데이터 저장 오류: {e}")
    
    async def get_unread_messages(self, limit: int = 10) -> List[Message]:
        """미확인 메시지 가져오기"""
        unread_messages = [
            msg for msg in self.messages 
            if not msg.get("is_read", False)
        ]
        
        # 최신 순으로 정렬
        unread_messages.sort(
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        
        result = []
        for msg_data in unread_messages[:limit]:
            try:
                message = Message(
                    msg_id=msg_data["msg_id"],
                    sender=msg_data["sender"],
                    recipient=msg_data["recipient"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    platform=msg_data["platform"],
                    is_read=msg_data.get("is_read", False),
                    priority=msg_data.get("priority")
                )
                result.append(message)
            except Exception as e:
                logger.error(f"메시지 파싱 오류: {e}")
        
        logger.info(f"📱 {len(result)}개의 미확인 메시지 수집")
        return result
    
    async def mark_as_read(self, msg_id: str) -> bool:
        """메시지를 읽음으로 표시"""
        for msg in self.messages:
            if msg["msg_id"] == msg_id:
                msg["is_read"] = True
                logger.info(f"✅ 메시지 읽음 처리: {msg_id}")
                return True
        return False


class SlackAdapter:
    """Slack API 어댑터 (향후 구현)"""
    
    def __init__(self, token: str):
        self.token = token
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Slack API 연결"""
        # TODO: 실제 Slack API 연동 구현
        logger.info("🔗 Slack API 연결 (구현 예정)")
        return False
    
    async def get_unread_messages(self, limit: int = 10) -> List[Message]:
        """Slack에서 미확인 메시지 가져오기"""
        # TODO: 실제 Slack API 호출 구현
        return []


class TeamsAdapter:
    """Microsoft Teams API 어댑터 (향후 구현)"""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Teams API 연결"""
        # TODO: 실제 Teams API 연동 구현
        logger.info("🔗 Teams API 연결 (구현 예정)")
        return False
    
    async def get_unread_messages(self, limit: int = 10) -> List[Message]:
        """Teams에서 미확인 메시지 가져오기"""
        # TODO: 실제 Teams API 호출 구현
        return []


class MessengerAdapter:
    """통합 메신저 어댑터"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.adapters = {}
        self.simulator = MessengerSimulator()
        self.sqlite_store = None  # ✅ 추가

        # ✅ SQLite 소스 활성화 (config로 제어)
        if self.config.get("source") == "sqlite":
            db_path = self.config.get("sqlite", {}).get("db_path")
            self.sqlite_store = SQLiteMessageStore(db_path)

        self._init_adapters()

    def _parse_ts(self, s: str) -> datetime:
        if not s:
            return datetime.now()
        try:
            if "T" in s:
                return datetime.fromisoformat(s)
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now()

    def _rows_to_messages(self, rows, limit: int):
        out = []
        for r in rows[:limit]:
            out.append(
                Message(
                    msg_id=str(r.get("id")),
                    sender=(r.get("username") or "unknown"),
                    recipient="me",
                    content=r.get("message") or "",
                    timestamp=self._parse_ts(r.get("timestamp") or ""),
                    platform=(r.get("room") or "messenger"),
                    is_read=False,
                    priority=None,
                )
            )
        return out

    
    def _init_adapters(self):
        """어댑터 초기화"""
        if "slack" in self.config:
            self.adapters["slack"] = SlackAdapter(self.config["slack"]["token"])
        
        if "teams" in self.config:
            teams_config = self.config["teams"]
            self.adapters["teams"] = TeamsAdapter(
                teams_config["client_id"],
                teams_config["client_secret"],
                teams_config["tenant_id"]
            )
    
    async def get_all_unread_messages(self, limit_per_platform: int = 10) -> List[Message]:
        """모든 플랫폼에서 미확인 메시지 수집"""
        all_messages = []
        
        if self.sqlite_store is not None:
            cfg = self.config.get("sqlite", {})
            rows = self.sqlite_store.fetch_messages(
                room=cfg.get("room"),
                since=cfg.get("since"),          # "YYYY-MM-DD HH:MM:SS" (옵션)
                limit=limit_per_platform,
            )
            all_messages.extend(self._rows_to_messages(rows, limit_per_platform))
        # 실제 API 어댑터들에서 메시지 수집
        for platform, adapter in self.adapters.items():
            try:
                if await adapter.connect():
                    messages = await adapter.get_unread_messages(limit_per_platform)
                    all_messages.extend(messages)
                    logger.info(f"📱 {platform}에서 {len(messages)}개 메시지 수집")
            except Exception as e:
                logger.error(f"{platform} 메시지 수집 오류: {e}")
        
        # 시뮬레이터에서도 메시지 수집 (개발/테스트용)
        if not all_messages or self.config.get("use_simulator", True):
            simulator_messages = await self.simulator.get_unread_messages(limit_per_platform)
            all_messages.extend(simulator_messages)
            logger.info(f"📱 시뮬레이터에서 {len(simulator_messages)}개 메시지 수집")
        
        # 타임스탬프 기준으로 정렬
        all_messages.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"📱 총 {len(all_messages)}개의 메신저 메시지 수집")
        return all_messages
    
    async def mark_message_as_read(self, msg_id: str, platform: str = None) -> bool:
        """메시지를 읽음으로 표시"""
        if platform and platform in self.adapters:
            adapter = self.adapters[platform]
            return await adapter.mark_as_read(msg_id)
        else:
            # 시뮬레이터에서 처리
            return await self.simulator.mark_as_read(msg_id)


# CSV 기반 메시지 로더 (대안)
class CSVMessageLoader:
    """CSV 파일에서 메시지 로드"""
    
    def __init__(self, csv_file: str):
        self.csv_file = Path(csv_file)
    
    def load_messages(self) -> List[Message]:
        """CSV에서 메시지 로드"""
        messages = []
        
        if not self.csv_file.exists():
            logger.warning(f"CSV 파일이 존재하지 않습니다: {self.csv_file}")
            return messages
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        message = Message(
                            msg_id=row["msg_id"],
                            sender=row["sender"],
                            recipient=row["recipient"],
                            content=row["content"],
                            timestamp=datetime.fromisoformat(row["timestamp"]),
                            platform=row["platform"],
                            is_read=row.get("is_read", "false").lower() == "true",
                            priority=row.get("priority")
                        )
                        messages.append(message)
                    except Exception as e:
                        logger.error(f"CSV 행 파싱 오류: {e}")
            
            logger.info(f"📱 CSV에서 {len(messages)}개 메시지 로드")
            
        except Exception as e:
            logger.error(f"CSV 로드 오류: {e}")
        
        return messages


# 테스트 함수
async def test_messenger_adapter():
    """메신저 어댑터 테스트"""
    config = {
        "use_simulator": True,
        "slack": {"token": "dummy_token"},
        "teams": {
            "client_id": "dummy_id",
            "client_secret": "dummy_secret",
            "tenant_id": "dummy_tenant"
        }
    }
    
    adapter = MessengerAdapter(config)
    messages = await adapter.get_all_unread_messages(5)
    
    print(f"📱 {len(messages)}개의 메신저 메시지 수집")
    for msg in messages:
        print(f"- {msg.platform}: {msg.content[:50]}... ({msg.sender})")


if __name__ == "__main__":
    asyncio.run(test_messenger_adapter())
