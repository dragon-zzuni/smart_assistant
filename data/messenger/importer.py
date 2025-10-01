# data/messenger/importer.py
import json
from pathlib import Path

class MessengerMsg:
    __slots__ = ("room", "username", "message", "timestamp", "type", "url", "filename")
    def __init__(self, d):
        self.room = d.get("room")
        self.username = d.get("username")
        self.message = d.get("message")
        self.timestamp = d.get("timestamp")
        self.type = d.get("type")
        self.url = d.get("url")
        self.filename = d.get("filename")


def _from_chat_logs_shape(data, rooms, include_system):
    """기존 chat_logs 형태([{"room","username","message","timestamp","type",...}]) 파싱"""
    items = []
    logs = data.get("chat_logs", data if isinstance(data, list) else [])
    for row in logs:
        msg = MessengerMsg(row)
        if not include_system and getattr(msg, "type", "chat") != "chat":
            continue
        if rooms and msg.room not in rooms:
            continue
        if (msg.type == "chat") and (not msg.message or not str(msg.message).strip()):
            continue
        items.append(msg)
    return items


def _from_portfolio_shape(data, rooms, include_system):
    """
    portfolio_webwite_run.json 형태 파싱:
    data["chat_messages"] 안의 채널들(developer, hana 등)에서
    {"body","sender","room_slug","sent_at"}를 공용 스키마로 변환
    """
    items = []
    chat = data.get("chat_messages") or {}
    for arr in chat.values():
        if not isinstance(arr, list):
            continue
        for it in arr:
            # 공용 필드로 매핑
            row = {
                "room": it.get("room_slug"),
                "username": it.get("sender") or "",
                "message": it.get("body") or it.get("message") or "",
                "timestamp": it.get("sent_at") or it.get("created_at"),
                "type": "chat",
                "url": None,
                "filename": None,
            }
            msg = MessengerMsg(row)
            if not include_system and getattr(msg, "type", "chat") != "chat":
                continue
            if rooms and msg.room not in rooms:
                continue
            if not msg.message or not str(msg.message).strip():
                continue
            items.append(msg)
    return items


def iter_messenger_messages(root="data/messenger", rooms=None, include_system=False, limit=None):
    """
    data/messenger 폴더의 *.json들을 순회하며
    - chat_logs 스키마
    - portfolio(=chat_messages) 스키마
    를 모두 지원해서 MessengerMsg 리스트로 반환.
    정렬은 호출측(main.collect_messages)에서 처리합니다.
    """
    p = Path(root)
    items = []

    for jf in sorted(p.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))

            if isinstance(data, dict) and "chat_messages" in data:
                # ✅ 새 스키마(포트폴리오) 지원
                items.extend(_from_portfolio_shape(data, rooms, include_system))
            else:
                # ✅ 기존 스키마(chat_logs 또는 리스트)
                items.extend(_from_chat_logs_shape(data, rooms, include_system))

        except Exception:
            # 파일 하나 읽기 실패해도 전체 흐름 깨지지 않도록 무시
            continue

    if limit:
        items = items[:limit]
    return items
