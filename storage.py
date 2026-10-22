"""SQLite for admin handoff. Use a persistent Railway volume for reliable restarts."""
import sqlite3
from pathlib import Path

class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS sessions (user_id INTEGER PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)')
        self.db.execute('CREATE TABLE IF NOT EXISTS routing (admin_message_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)')
        self.db.commit()

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
