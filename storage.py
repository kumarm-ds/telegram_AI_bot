"""SQLite for admin handoff. Use a persistent Railway volume for reliable restarts."""
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
        self.lock = threading.RLock()
        self.db.execute('CREATE TABLE IF NOT EXISTS sessions (user_id INTEGER PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)')
        self.db.execute('CREATE TABLE IF NOT EXISTS routing (admin_message_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS chat_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, utc_time TEXT NOT NULL, user_id INTEGER NOT NULL, sender TEXT NOT NULL, event TEXT NOT NULL, message TEXT NOT NULL)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_user_id ON chat_logs(user_id)')
        self.db.commit()

    def log(self, user_id, sender, event, message):
        with self.lock:
            self.db.execute('INSERT INTO chat_logs (utc_time, user_id, sender, event, message) VALUES (?,?,?,?,?)',
                (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), user_id, sender, event, str(message)))
            self.db.commit()

    def get_logs(self, limit=100000):
        with self.lock:
            return self.db.execute('SELECT id,utc_time,user_id,sender,event,message FROM chat_logs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()

    def search_logs(self, q='', user='', page=1, page_size=50):
        where = []; params = []
        if q:
            where.append('message LIKE ?'); params.append('%' + q + '%')
        if user:
            if not user.isdecimal():
                return [], 0
            where.append('user_id=?'); params.append(int(user))
        clause = ' WHERE ' + ' AND '.join(where) if where else ''
        with self.lock:
            total = self.db.execute('SELECT COUNT(*) FROM chat_logs' + clause, params).fetchone()[0]
            rows = self.db.execute('SELECT id,utc_time,user_id,sender,event,message FROM chat_logs' + clause + ' ORDER BY id DESC LIMIT ? OFFSET ?', params + [page_size, (page-1)*page_size]).fetchall()
        return rows, total

    def active(self, user_id):
        row = self.db.execute('SELECT active FROM sessions WHERE user_id=?', (user_id,)).fetchone()
        return bool(row and row[0])

    def set_active(self, user_id, active):
        self.db.execute('INSERT INTO sessions (user_id,active) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET active=excluded.active', (user_id, int(active)))
        self.db.commit()

    def route(self, admin_message_id, user_id):
        self.db.execute('INSERT OR REPLACE INTO routing VALUES (?,?)', (admin_message_id, user_id))
        self.db.commit()

    def user_for(self, admin_message_id):
        row = self.db.execute('SELECT user_id FROM routing WHERE admin_message_id=?', (admin_message_id,)).fetchone()
        return row[0] if row else None
