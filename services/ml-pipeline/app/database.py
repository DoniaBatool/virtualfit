"""
NeonDB (PostgreSQL) connection and wardrobe CRUD operations.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_conn = None


def _get_conn():
    global _conn
    # Test if existing connection is alive
    if _conn is not None:
        try:
            _conn.cursor().execute("SELECT 1")
            return _conn
        except Exception:
            _conn = None

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.warning("DATABASE_URL not set — wardrobe DB disabled")
        return None

    try:
        import psycopg2
        _conn = psycopg2.connect(db_url)
        _conn.autocommit = True
        logger.info("✅ NeonDB connected")
        return _conn
    except Exception as e:
        logger.warning(f"NeonDB connection failed: {e}")
        return None


def save_wardrobe_item(
    feature: str,
    result_url: str,
    user_id: str = "guest",
    settings: Optional[dict] = None,
) -> Optional[dict]:
    conn = _get_conn()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO wardrobe (user_id, feature, result_url, settings)
                   VALUES (%s, %s, %s, %s) RETURNING id, created_at""",
                (user_id, feature, result_url, json.dumps(settings or {})),
            )
            row = cur.fetchone()
            return {"id": str(row[0]), "created_at": str(row[1])}
    except Exception as e:
        logger.warning(f"DB save failed: {e}")
        return None


def get_wardrobe_items(user_id: str = "guest") -> list:
    conn = _get_conn()
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, feature, result_url, created_at
                   FROM wardrobe WHERE user_id = %s
                   ORDER BY created_at DESC LIMIT 100""",
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "feature": r[1],
                    "result_image": r[2],
                    "name": f"{r[1].replace('-', ' ').title()} Try-On",
                    "saved_at": str(r[3]),
                }
                for r in rows
            ]
    except Exception as e:
        logger.warning(f"DB fetch failed: {e}")
        return []


def delete_wardrobe_item(item_id: str, user_id: str = "guest") -> bool:
    conn = _get_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM wardrobe WHERE id = %s AND user_id = %s",
                (int(item_id), user_id),
            )
            return cur.rowcount > 0
    except Exception as e:
        logger.warning(f"DB delete failed: {e}")
        return False
