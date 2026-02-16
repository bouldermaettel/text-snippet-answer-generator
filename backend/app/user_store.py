"""SQLite user store: init DB, CRUD, password hash/verify."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import bcrypt

from .config import get_settings

# bcrypt has a 72-byte limit; truncate to avoid ValueError with long passwords
_BCRYPT_MAX_BYTES = 72


def _get_db_path() -> Path:
    p = Path(get_settings().database_url)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create users table if it does not exist; add status column if missing."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        )
        # Migration: add status column to existing tables that don't have it
        cur = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        if "status" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
            conn.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        raw = raw[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    raw = plain.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        raw = raw[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(raw, hashed.encode("ascii"))
    except Exception:
        return False


def get_user_by_id(user_id: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, role, status, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "status": row["status"] if "status" in row.keys() else "active",
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, role, status, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "status": row["status"] if "status" in row.keys() else "active",
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def create_user(
    email: str,
    password: str,
    role: str = "user",
    status: str = "active",
) -> dict:
    email = email.strip().lower()
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, status, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (user_id, email, password_hash, role, status),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "id": user_id,
        "email": email,
        "role": role,
        "status": status,
        "created_at": None,
    }


def list_users() -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, status, created_at FROM users ORDER BY created_at"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "email": row["email"],
                "role": row["role"],
                "status": row["status"] if "status" in row.keys() else "active",
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def set_user_status(user_id: str, status: str) -> bool:
    conn = _get_connection()
    try:
        cur = conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_user(user_id: str) -> bool:
    conn = _get_connection()
    try:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def count_admins() -> int:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'admin'"
        ).fetchone()
        return row["n"] if row else 0
    finally:
        conn.close()
