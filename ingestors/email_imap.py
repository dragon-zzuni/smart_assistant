# -*- coding: utf-8 -*-
"""
Email IMAP 수집기 - 네이버, Gmail 등 IMAP 지원 이메일 서비스에서 메일 수집
"""
import imaplib
import ssl
import asyncio
import logging
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header, make_header
from typing import Dict, List, Optional, Tuple
import re
import json
from dataclasses import dataclass

from config.settings import EMAIL_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """이메일 메시지 데이터 클래스"""
    msg_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    attachments: List[str]
    is_read: bool = False
    priority: Optional[str] = None
    labels: List[str] = None
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "msg_id": self.msg_id,
            "subject": self.subject,
            "sender": self.sender,
            "recipient": self.recipient,
            "date": self.date.isoformat(),
            "body": self.body,
            "attachments": self.attachments,
            "is_read": self.is_read,
            "priority": self.priority,
            "labels": self.labels or []
        }


class EmailIMAPCollector:
    """IMAP 이메일 수집기"""
    
    def __init__(self, email: str, password: str, provider: str = "naver"):
        self.email = email
        self.password = password
        self.provider = provider.lower()
        self.config = EMAIL_CONFIG.get(self.provider, EMAIL_CONFIG["naver"])
        
        self.client: Optional[imaplib.IMAP4_SSL] = None
        self._is_connected = False
        
    async def connect(self) -> bool:
        """IMAP 서버에 연결"""
        try:
            self.client = imaplib.IMAP4_SSL(
                self.config["imap_host"], 
                self.config["imap_port"]
            )
            self.client.login(self.email, self.password)
            self._is_connected = True
            logger.info(f"✅ {self.provider} IMAP 연결 성공: {self.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ IMAP 연결 실패: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """IMAP 연결 종료"""
        try:
            if self.client and self._is_connected:
                self.client.close()
                self.client.logout()
                self._is_connected = False
                logger.info("🔌 IMAP 연결 종료")
        except Exception as e:
            logger.error(f"연결 종료 오류: {e}")
    
    async def get_unread_emails(self, limit: int = 10) -> List[EmailMessage]:
        """미확인 이메일 가져오기"""
        if not self._is_connected or not self.client:
            await self.connect()
        
        if not self._is_connected or not self.client:
            return []
        
        try:
            # INBOX 선택
            typ, data = self.client.select("INBOX")
            if typ != "OK":
                logger.error("INBOX 선택 실패")
                return []
            
            # 미확인 이메일 검색
            typ, data = self.client.search(None, "UNSEEN")
            if typ != "OK":
                logger.error("미확인 이메일 검색 실패")
                return []
            
            msg_ids = data[0].split() if data and data[0] else []
            msg_ids = list(reversed(msg_ids))[-limit:]  # 최신 순으로 정렬
            
            emails = []
            for msg_id in msg_ids:
                if not self._is_connected or not self.client:
                    logger.warning("연결이 끊어져서 이메일 수집 중단")
                    break
                    
                email_data = await self._fetch_email_data(msg_id)
                if email_data:
                    emails.append(email_data)
            
            logger.info(f"📧 {len(emails)}개의 미확인 이메일 수집")
            return emails
            
        except Exception as e:
            logger.error(f"이메일 수집 오류: {e}")
            # 연결 상태 초기화
            self._is_connected = False
            self.client = None
            return []
    
    async def get_emails_since(self, since_date: datetime, limit: int = 50) -> List[EmailMessage]:
        """특정 날짜 이후 이메일 가져오기"""
        if not self._is_connected:
            await self.connect()
        
        if not self._is_connected:
            return []
        
        try:
            self.client.select("INBOX")
            
            # 날짜 형식 변환 (DD-MMM-YYYY)
            date_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f'SINCE "{date_str}"'
            
            typ, data = self.client.search(None, search_criteria)
            if typ != "OK":
                return []
            
            msg_ids = data[0].split() if data and data[0] else []
            msg_ids = list(reversed(msg_ids))[-limit:]
            
            emails = []
            for msg_id in msg_ids:
                email_data = await self._fetch_email_data(msg_id)
                if email_data:
                    emails.append(email_data)
            
            logger.info(f"📧 {len(emails)}개의 이메일 수집 (since {date_str})")
            return emails
            
        except Exception as e:
            logger.error(f"이메일 수집 오류: {e}")
            return []
    
    async def _fetch_email_data(self, msg_id: bytes) -> Optional[EmailMessage]:
        """이메일 데이터 추출"""
        try:
            if not self._is_connected or not self.client:
                logger.warning("연결이 끊어져서 이메일 데이터 추출 불가")
                return None
                
            typ, data = self.client.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not data or not isinstance(data[0], tuple):
                return None
            
            raw_email = data[0][1]
            msg = message_from_bytes(raw_email)
            
            # 기본 정보 추출
            subject = self._decode_mime_words(msg.get("Subject"))
            sender = self._decode_mime_words(msg.get("From"))
            recipient = self._decode_mime_words(msg.get("To"))
            date_str = msg.get("Date", "")
            
            # 날짜 파싱
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # 본문 추출
            body = self._extract_text_from_email(msg)
            
            # 첨부파일 정보
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        if filename:
                            attachments.append(self._decode_mime_words(filename))
            
            return EmailMessage(
                msg_id=msg_id.decode(),
                subject=subject,
                sender=sender,
                recipient=recipient,
                date=date,
                body=body,
                attachments=attachments,
                is_read=False
            )
            
        except Exception as e:
            logger.error(f"이메일 데이터 추출 오류: {e}")
            return None
    
    async def mark_as_read(self, msg_id: str) -> bool:
        """이메일을 읽음으로 표시"""
        try:
            if not self._is_connected:
                return False
            
            self.client.store(msg_id.encode(), "+FLAGS", "(\\Seen)")
            logger.info(f"✅ 이메일 읽음 처리: {msg_id}")
            return True
            
        except Exception as e:
            logger.error(f"읽음 처리 오류: {e}")
            return False
    
    async def add_label(self, msg_id: str, label: str) -> bool:
        """이메일에 라벨 추가 (Gmail)"""
        try:
            if not self._is_connected or self.provider != "gmail":
                return False
            
            self.client.store(msg_id.encode(), "+X-GM-LABELS", f'"{label}"')
            logger.info(f"🏷️ 라벨 추가: {label}")
            return True
            
        except Exception as e:
            logger.error(f"라벨 추가 오류: {e}")
            return False
    
    def _decode_mime_words(self, value: Optional[str]) -> str:
        """MIME 인코딩된 헤더 디코딩"""
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value
    
    def _extract_text_from_email(self, msg) -> str:
        """이메일에서 텍스트 추출"""
        if msg.is_multipart():
            parts = []
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", "")).lower()
                
                if ctype == "text/plain" and "attachment" not in disp:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            text = payload.decode(charset, errors="replace")
                            parts.append(text)
                    except Exception:
                        continue
            
            if parts:
                return "\n".join(parts).strip()
                
            # HTML이 있으면 텍스트로 변환
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", "")).lower()
                
                if ctype == "text/html" and "attachment" not in disp:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            html = payload.decode(charset, errors="replace")
                            return self._strip_html(html)
                    except Exception:
                        continue
            return ""
        else:
            ctype = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    if ctype == "text/html":
                        return self._strip_html(text)
                    return text
            except Exception:
                pass
            return msg.get_payload() or ""
    
    def _strip_html(self, html: str) -> str:
        """HTML 태그 제거"""
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# 테스트 함수
async def test_email_collector():
    """이메일 수집기 테스트"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not email or not password:
        print("❌ 환경변수에 EMAIL_ADDRESS, EMAIL_PASSWORD를 설정해주세요.")
        return
    
    collector = EmailIMAPCollector(email, password, "naver")
    
    try:
        if await collector.connect():
            emails = await collector.get_unread_emails(5)
            print(f"📧 {len(emails)}개의 미확인 이메일 수집")
            
            for email in emails:
                print(f"- {email.subject} ({email.sender})")
        
    finally:
        await collector.disconnect()


if __name__ == "__main__":
    asyncio.run(test_email_collector())
