import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from psycopg.types.json import Jsonb
from homate.infrastructure.postgres.connection import connect


def decode(row):
    row = dict(row)
    for key in ("arguments", "result"):
        if isinstance(row.get(key), str): row[key] = json.loads(row[key])
    for key in ("id", "request_id"):
        row[key] = str(row[key])
    return row


class PostgresActionRepository:
    def __init__(self, url): self.url = url

    def propose(self, user, request_id, tool, arguments, summary, ttl):
        with connect(self.url) as conn:
            conn.execute("""INSERT INTO agent_actions(id,home_id,user_id,request_id,tool,arguments,summary,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,request_id) DO NOTHING""",
                (uuid4(), user['home_id'], user['id'], request_id, tool, Jsonb(arguments), summary,
                 datetime.now(timezone.utc) + timedelta(seconds=ttl)))
            row = decode(conn.execute("SELECT * FROM agent_actions WHERE user_id=%s AND request_id=%s", (user['id'], request_id)).fetchone())
            if row['tool'] != tool or row['arguments'] != arguments:
                raise ValueError("Mã yêu cầu đã được dùng cho thao tác khác")
            return row

    def claim(self, user, identifier, approved):
        with connect(self.url) as conn:
            row = conn.execute("SELECT * FROM agent_actions WHERE id=%s AND user_id=%s AND home_id=%s FOR UPDATE", (identifier, user['id'], user['home_id'])).fetchone()
            if not row: raise LookupError("Không tìm thấy yêu cầu xác nhận")
            row = decode(row)
            if row['status'] != 'pending': return row
            expired = datetime.fromisoformat(row['expires_at']) <= datetime.now(timezone.utc)
            state = 'expired' if expired else ('executing' if approved else 'rejected')
            conn.execute("UPDATE agent_actions SET status=%s WHERE id=%s", (state, identifier))
            row['status'] = state
            row['claimed'] = state == 'executing'
            return row

    def finish(self, identifier, status, result):
        with connect(self.url) as conn:
            return decode(conn.execute("UPDATE agent_actions SET status=%s,result=%s WHERE id=%s RETURNING *", (status, Jsonb(result), identifier)).fetchone())
