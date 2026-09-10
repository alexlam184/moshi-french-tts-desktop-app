import sqlite3
from pathlib import Path


class HistoryStore:
    MAX_ITEMS = 20

    def __init__(self, data_dir: Path):
        self.connection = sqlite3.connect(data_dir / "history.sqlite3")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY, source_text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        self.connection.commit()

    def save(self, source_text: str) -> None:
        self.connection.execute("INSERT INTO history(source_text) VALUES (?)", (source_text,))
        # Keep the newest entries and discard the oldest first (FIFO).
        self.connection.execute(
            "DELETE FROM history WHERE id NOT IN "
            "(SELECT id FROM history ORDER BY id DESC LIMIT ?)",
            (self.MAX_ITEMS,),
        )
        self.connection.commit()

    def recent(self, limit: int = MAX_ITEMS) -> list[tuple[str, str]]:
        return self.connection.execute(
            "SELECT source_text, created_at FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    def close(self) -> None:
        self.connection.close()
