import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from psycopg.types.json import Jsonb
from homate.application.agent_workflow import WorkflowConflict
from homate.infrastructure.postgres.connection import connect


def decoded(row):
    if row is None:
        raise LookupError('Không tìm thấy hội thoại hoặc kế hoạch')
    result = dict(row)
    for key in ('state', 'messages', 'response', 'arguments', 'prepared', 'depends_on', 'result'):
        if isinstance(result.get(key), str):
            result[key] = json.loads(result[key])
    for key in ('id', 'session_id', 'request_id', 'busy_request', 'plan_id'):
        if result.get(key) is not None:
            result[key] = str(result[key])
    return result


def now():
    return datetime.now(timezone.utc)


class PostgresWorkflowRepository:
    def __init__(self, url):
        self.url = url

    def _settled_state(self, conn, session_id, plan_id):
        state = decoded(conn.execute('SELECT state FROM agent_sessions WHERE id=%s', (session_id,)).fetchone())['state']
        memory = state.get('conversation')
        if not isinstance(memory, dict):
            return {}
        receipt = self._plan(conn, plan_id)
        return {'conversation': {**memory, 'observations': [], 'execution': {
            'plan_id': str(plan_id), 'status': receipt['status'],
            'steps': [{key: step[key] for key in ('ordinal', 'summary', 'status', 'result')}
                      for step in receipt['steps']]}}}

    def _session(self, conn, user, identifier, lock=False):
        return decoded(conn.execute('SELECT * FROM agent_sessions WHERE id=%s AND user_id=%s AND home_id=%s'
            + (' FOR UPDATE' if lock else ''), (identifier, user['id'], user['home_id'])).fetchone())

    def _plan(self, conn, identifier, internal=False):
        row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s', (identifier,)).fetchone())
        steps = [decoded(item) for item in conn.execute('SELECT * FROM agent_plan_steps WHERE plan_id=%s ORDER BY ordinal', (identifier,)).fetchall()]
        public_steps = [{k: v for k, v in step.items() if internal or k != 'prepared'} for step in steps]
        review = []
        for step in steps:
            review.append(f'{step["ordinal"] + 1}. {step["summary"]}')
            review.extend(str(line) for line in step['prepared'].get('review', []))
        return {**row, 'kind': 'plan', 'tool': 'execute_plan', 'plan_version': row['version'],
                'conversation_id': row['session_id'], 'steps': public_steps,
                'arguments': {'review': review},
                'recovery_required': row['status'] == 'executing' and
                    datetime.fromisoformat(row['updated_at']) < now() - timedelta(minutes=5)}

    def begin(self, user, request_id, input_hash, session_id=None, expected_version=None):
        with connect(self.url) as conn:
            # Serialize duplicate requests even when the first request creates a session.
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (user['id'] + ':' + request_id,))
            turn = conn.execute('SELECT * FROM agent_turns WHERE user_id=%s AND request_id=%s', (user['id'], request_id)).fetchone()
            if turn:
                turn = decoded(turn)
                if turn['input_hash'] != input_hash:
                    raise WorkflowConflict('Mã yêu cầu đã dùng cho nội dung khác')
                session = self._session(conn, user, turn['session_id'], True)
                if turn['status'] == 'completed':
                    return {'cached': True, 'response': turn['response']}
                if turn['status'] == 'processing' and session['busy_until'] and datetime.fromisoformat(session['busy_until']) > now():
                    raise WorkflowConflict('Yêu cầu đang được xử lý; không gửi đồng thời')
                if turn['base_version'] != session['version']:
                    raise WorkflowConflict('Hội thoại đã thay đổi; hãy tải lại trước khi gửi yêu cầu mới')
                session_id = session['id']
            elif session_id:
                session = self._session(conn, user, session_id, True)
            else:
                session_id = str(uuid4())
                session = decoded(conn.execute('INSERT INTO agent_sessions(id,home_id,user_id,expires_at) VALUES(%s,%s,%s,%s) RETURNING *',
                    (session_id, user['home_id'], user['id'], now() + timedelta(minutes=30))).fetchone())
            if session['status'] == 'executing':
                raise WorkflowConflict('Kế hoạch đang thực thi; hãy kiểm tra kết quả trước khi sửa')
            if session['busy_request'] and session['busy_request'] != request_id and datetime.fromisoformat(session['busy_until']) > now():
                raise WorkflowConflict('Hội thoại đang xử lý một yêu cầu khác')
            if expected_version is not None and expected_version != session['version']:
                raise WorkflowConflict('Phiên bản hội thoại đã thay đổi; hãy tải lại')
            if datetime.fromisoformat(session['expires_at']) <= now():
                conn.execute("UPDATE agent_plans SET status='expired' WHERE session_id=%s AND status='pending'", (session_id,))
                session['state'], session['messages'], session['status'] = {}, [], 'idle'
                conn.execute("UPDATE agent_sessions SET state='{}',messages='[]',status='idle' WHERE id=%s", (session_id,))
            conn.execute('''INSERT INTO agent_turns(request_id,user_id,session_id,input_hash,status,base_version)
                VALUES(%s,%s,%s,%s,'processing',%s) ON CONFLICT(user_id,request_id)
                DO UPDATE SET status='processing',created_at=now()''',
                (request_id, user['id'], session_id, input_hash, session['version']))
            lease = str(uuid4())
            conn.execute('UPDATE agent_sessions SET busy_request=%s,busy_lease=%s,busy_until=%s WHERE id=%s',
                (request_id, lease, now() + timedelta(minutes=5), session_id))
            return {'cached': False, 'session': session, 'lease_id': lease}

    def commit(self, user, request_id, state, response, invalidate, steps, summary, ttl, lease_id):
        with connect(self.url) as conn:
            turn = decoded(conn.execute('SELECT * FROM agent_turns WHERE user_id=%s AND request_id=%s', (user['id'], request_id)).fetchone())
            session = self._session(conn, user, turn['session_id'], True)
            if turn['status'] == 'completed':
                return turn['response']
            if turn['status'] != 'processing' or session['busy_request'] != request_id or str(session['busy_lease']) != lease_id or session['version'] != turn['base_version'] or datetime.fromisoformat(session['busy_until']) <= now():
                raise WorkflowConflict('Lượt xử lý đã hết hạn hoặc hội thoại đã thay đổi')
            version, plan_version = session['version'] + 1, session['plan_version'] + int(invalidate)
            invalidated, invalidated_status = [], None
            if invalidate:
                status = 'cancelled' if state.get('cancelled') else 'superseded'
                invalidated = [str(row['id']) for row in conn.execute("SELECT id FROM agent_plans WHERE session_id=%s AND status='pending'", (session['id'],)).fetchall()]
                invalidated_status = status
                conn.execute('UPDATE agent_plans SET status=%s,updated_at=now() WHERE session_id=%s AND status=\'pending\'', (status, session['id']))
            if steps:
                if not invalidate:
                    raise ValueError('Kế hoạch mới phải tăng phiên bản')
                identifier = str(uuid4())
                conn.execute('INSERT INTO agent_plans(id,session_id,version,summary,expires_at) VALUES(%s,%s,%s,%s,%s)',
                    (identifier, session['id'], plan_version, summary, now() + timedelta(seconds=ttl)))
                for index, step in enumerate(steps):
                    conn.execute('''INSERT INTO agent_plan_steps(plan_id,ordinal,tool,arguments,prepared,summary,depends_on)
                        VALUES(%s,%s,%s,%s,%s,%s,%s)''', (identifier, index, step['tool'], Jsonb(step['arguments']),
                        Jsonb(step['prepared']), step['summary'], Jsonb(step.get('depends_on', []))))
            active = conn.execute("SELECT id FROM agent_plans WHERE session_id=%s AND status='pending' ORDER BY version DESC LIMIT 1", (session['id'],)).fetchone()
            actions = [self._plan(conn, active['id'])] if active else []
            status = 'pending' if actions else ('clarifying' if state.get('draft') else 'idle')
            result = {**response, 'pending_actions': actions, 'conversation_id': session['id'],
                      'conversation_version': version, 'dialogue_state': status,
                      'invalidated_plan_ids': invalidated, 'invalidated_status': invalidated_status}
            messages = (session['messages'] + [{'role': 'user', 'content': response.pop('_user_text', '')},
                {'role': 'assistant', 'content': response['reply'], 'sources': response.get('sources', [])}])[-60:]
            result.pop('_user_text', None)
            saved_state = {key: value for key, value in state.items() if key != 'cancelled'}
            conn.execute('''UPDATE agent_sessions SET version=%s,plan_version=%s,status=%s,state=%s,messages=%s,
                busy_request=NULL,busy_lease=NULL,busy_until=NULL,expires_at=%s,updated_at=now() WHERE id=%s''',
                (version, plan_version, status, Jsonb(saved_state), Jsonb(messages), now() + timedelta(minutes=30), session['id']))
            conn.execute("UPDATE agent_turns SET status='completed',response=%s WHERE user_id=%s AND request_id=%s", (Jsonb(result), user['id'], request_id))
            return result

    def abort(self, user, request_id, lease_id):
        with connect(self.url) as conn:
            turn = conn.execute('SELECT session_id FROM agent_turns WHERE user_id=%s AND request_id=%s', (user['id'], request_id)).fetchone()
            if not turn:
                return
            session = self._session(conn, user, str(turn['session_id']), True)
            if session['busy_request'] != request_id or str(session['busy_lease']) != lease_id:
                return
            conn.execute("UPDATE agent_turns SET status='failed' WHERE user_id=%s AND request_id=%s AND status='processing'", (user['id'], request_id))
            conn.execute('UPDATE agent_sessions SET busy_request=NULL,busy_lease=NULL,busy_until=NULL WHERE user_id=%s AND busy_request=%s', (user['id'], request_id))

    def fetch(self, user, session_id):
        with connect(self.url) as conn:
            session = self._session(conn, user, session_id)
            row = conn.execute('SELECT id FROM agent_plans WHERE session_id=%s ORDER BY version DESC LIMIT 1', (session_id,)).fetchone()
            return {**{k: session[k] for k in ('id', 'version', 'status', 'state', 'messages', 'expires_at')},
                    'plan': self._plan(conn, row['id']) if row else None,
                    'expired': datetime.fromisoformat(session['expires_at']) <= now()}

    def get_plan(self, user, plan_id):
        with connect(self.url) as conn:
            row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s', (plan_id,)).fetchone())
            self._session(conn, user, row['session_id'])
            return self._plan(conn, plan_id)

    def close(self, user, session_id):
        with connect(self.url) as conn:
            session = self._session(conn, user, session_id, True)
            if session['status'] == 'executing' or session['busy_request'] and datetime.fromisoformat(session['busy_until']) > now():
                raise WorkflowConflict('Hội thoại đang được xử lý; hãy chờ kết quả trước khi đóng')
            conn.execute("UPDATE agent_plans SET status='cancelled',updated_at=now() WHERE session_id=%s AND status='pending'", (session_id,))
            conn.execute("UPDATE agent_sessions SET status='idle',state='{}',version=version+1,plan_version=plan_version+1 WHERE id=%s", (session_id,))

    def claim(self, user, plan_id, version, approved):
        with connect(self.url) as conn:
            row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s', (plan_id,)).fetchone())
            session = self._session(conn, user, row['session_id'], True)
            plan = self._plan(conn, plan_id, internal=True)
            if plan['version'] != version:
                raise WorkflowConflict('Phiên bản xác nhận không khớp kế hoạch')
            if plan['status'] in {'superseded', 'cancelled'} or plan['version'] != session['plan_version']:
                raise WorkflowConflict('Kế hoạch đã được thay thế hoặc hủy; hãy dùng phiên bản mới')
            if plan['status'] != 'pending':
                return self._plan(conn, plan_id)
            if session['busy_request'] and datetime.fromisoformat(session['busy_until']) > now():
                raise WorkflowConflict('Đang cập nhật hội thoại; hãy chờ kết quả trước khi xác nhận')
            status = 'expired' if datetime.fromisoformat(plan['expires_at']) <= now() else ('executing' if approved else 'rejected')
            conn.execute('UPDATE agent_plans SET status=%s,updated_at=now() WHERE id=%s', (status, plan_id))
            conn.execute('UPDATE agent_sessions SET status=%s WHERE id=%s', ('executing' if status == 'executing' else 'idle', session['id']))
            if status != 'executing':
                conn.execute("UPDATE agent_plan_steps SET status='skipped' WHERE plan_id=%s AND status='pending'", (plan_id,))
                conn.execute('UPDATE agent_sessions SET state=%s WHERE id=%s',
                             (Jsonb(self._settled_state(conn, session['id'], plan_id)), session['id']))
                return self._plan(conn, plan_id)
            plan['status'], plan['claimed'] = 'executing', True
            return plan

    def start_step(self, plan_id, ordinal):
        with connect(self.url) as conn:
            conn.execute('SELECT id FROM agent_plans WHERE id=%s FOR UPDATE', (plan_id,)).fetchone()
            row = conn.execute("""UPDATE agent_plan_steps SET status='running',updated_at=now()
                WHERE plan_id=%s AND ordinal=%s AND status='pending'
                AND EXISTS(SELECT 1 FROM agent_plans WHERE id=%s AND status='executing') RETURNING ordinal""", (plan_id, ordinal, plan_id)).fetchone()
            if not row:
                raise WorkflowConflict('Bước đã được nhận xử lý; không thực thi lại')
            conn.execute('UPDATE agent_plans SET updated_at=now() WHERE id=%s', (plan_id,))

    def finish_step(self, plan_id, ordinal, status, result):
        with connect(self.url) as conn:
            conn.execute('SELECT id FROM agent_plans WHERE id=%s FOR UPDATE', (plan_id,)).fetchone()
            row = conn.execute("""UPDATE agent_plan_steps SET status=%s,result=%s,updated_at=now()
                WHERE plan_id=%s AND ordinal=%s AND status='running'
                AND EXISTS(SELECT 1 FROM agent_plans WHERE id=%s AND status='executing') RETURNING ordinal""",
                (status, Jsonb(result), plan_id, ordinal, plan_id)).fetchone()
            conn.execute("UPDATE agent_plans SET updated_at=now() WHERE id=%s AND status='executing'", (plan_id,))
            return bool(row)

    def finish_plan(self, plan_id, status, result):
        with connect(self.url) as conn:
            owner = conn.execute('SELECT session_id FROM agent_plans WHERE id=%s', (plan_id,)).fetchone()
            session = decoded(conn.execute('SELECT * FROM agent_sessions WHERE id=%s FOR UPDATE', (owner['session_id'],)).fetchone())
            row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s FOR UPDATE', (plan_id,)).fetchone())
            if row['status'] != 'executing':
                return self._plan(conn, plan_id)
            conn.execute("UPDATE agent_plan_steps SET status='skipped',updated_at=now() WHERE plan_id=%s AND status='pending'", (plan_id,))
            conn.execute('UPDATE agent_plans SET status=%s,result=%s,updated_at=now() WHERE id=%s', (status, Jsonb(result), plan_id))
            message = {'role': 'assistant', 'content': row['summary'] + ': ' + result['message']}
            conn.execute("UPDATE agent_sessions SET status='idle',state=%s,messages=%s,updated_at=now() WHERE id=%s",
                         (Jsonb(self._settled_state(conn, row['session_id'], plan_id)), Jsonb((session['messages'] + [message])[-60:]), row['session_id']))
            return self._plan(conn, plan_id)

    def recover(self, user, plan_id, version):
        with connect(self.url) as conn:
            row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s', (plan_id,)).fetchone())
            session = self._session(conn, user, row['session_id'], True)
            row = decoded(conn.execute('SELECT * FROM agent_plans WHERE id=%s FOR UPDATE', (plan_id,)).fetchone())
            if row['version'] != version:
                raise WorkflowConflict('Phiên bản kế hoạch không khớp')
            if row['status'] != 'executing':
                return self._plan(conn, plan_id)
            if datetime.fromisoformat(row['updated_at']) > now() - timedelta(minutes=5):
                raise WorkflowConflict('Kế hoạch vẫn đang xử lý; chưa thể đóng như phiên gián đoạn')
            message = 'Đã đóng kế hoạch sau kiểm tra thủ công. Bước đang chạy có kết quả chưa xác định và có thể có tác động muộn; không tự chạy lại.'
            conn.execute("UPDATE agent_plans SET status='failed',result=%s,updated_at=now() WHERE id=%s", (Jsonb({'message': message}), plan_id))
            conn.execute("UPDATE agent_plan_steps SET status='failed',result=%s WHERE plan_id=%s AND status='running'", (Jsonb({'message': message}), plan_id))
            conn.execute("UPDATE agent_plan_steps SET status='skipped' WHERE plan_id=%s AND status='pending'", (plan_id,))
            messages = (session['messages'] + [{'role': 'assistant', 'content': message}])[-60:]
            conn.execute("UPDATE agent_sessions SET status='idle',state=%s,messages=%s WHERE id=%s",
                         (Jsonb(self._settled_state(conn, session['id'], plan_id)), Jsonb(messages), session['id']))
            return self._plan(conn, plan_id)
