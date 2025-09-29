# messenger_adapter/sqlite_adapter.py
from pathlib import Path
import os, sqlite3
from typing import List, Optional, Dict, Any

class SQLiteMessageStore:
    def __init__(self, db_path: Optional[Path] = None):
        root = Path(__file__).resolve().parents[1]
        self.db_path = Path(os.getenv("MESSENGER_DB_PATH", root / "data" / "messenger" / "messages.db"))
        if db_path:
            self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def fetch_messages(
        self,
        room: Optional[str] = None,
        since: Optional[str] = None,  # 'YYYY-MM-DD HH:MM:SS'
        until: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        q = "SELECT * FROM messages WHERE 1=1"
        params = []
        if room:
            q += " AND room = ?"; params.append(room)
        if since:
            q += " AND timestamp >= ?"; params.append(since)
        if until:
            q += " AND timestamp < ?"; params.append(until)
        q += " ORDER BY timestamp ASC LIMIT ?"; params.append(limit)
        return [dict(r) for r in self.conn.execute(q, params)]

    def close(self):
        self.conn.close()
