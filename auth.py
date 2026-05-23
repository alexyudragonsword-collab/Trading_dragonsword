"""User authentication — SQLite + PBKDF2-HMAC-SHA256, no extra dependencies."""

import hashlib
import hmac
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("CACHE_DIR", ".cache")) / "users.db"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username     TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _hash(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return dk.hex(), salt


def register(email: str, password: str) -> bool | str:
    """Return True on success, or an error string."""
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        return "请输入有效的邮箱地址"
    if len(password) < 6:
        return "密码至少 6 个字符"
    with _conn() as c:
        if c.execute("SELECT 1 FROM users WHERE username=?", (email,)).fetchone():
            return "该邮箱已注册"
        pw_hash, salt = _hash(password)
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (email, f"{salt}${pw_hash}"),
        )
    return True


def verify(email: str, password: str) -> bool:
    email = email.strip().lower()
    with _conn() as c:
        row = c.execute(
            "SELECT password_hash FROM users WHERE username=?", (email,)
        ).fetchone()
    if not row:
        return False
    salt, stored = row[0].split("$", 1)
    computed, _ = _hash(password, salt)
    return hmac.compare_digest(computed, stored)
