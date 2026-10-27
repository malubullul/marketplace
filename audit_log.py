"""Private, transactional audit events. Never store credentials or buyer addresses."""
import json
import re
import secrets
import time
from flask import g, jsonify, request


class AuditLog:
    def __init__(self, app, db, owner_required, fail):
        self.db = db
        self.postgres = bool(app.config['DATABASE_URL'])
        app.audit_log = self

        @app.get('/api/admin/activity')
        @owner_required
        def activity():
            cursor = request.args.get('cursor', '')
            try:
                limit = int(request.args.get('limit', '30'))
                if not 1 <= limit <= 100 or (cursor and not re.fullmatch(r'audit:\d{20}:[a-f0-9]{16}', cursor)):
                    raise ValueError()
            except ValueError:
                return fail('Halaman aktivitas tidak valid.')
            rows = db().execute("SELECT key,value FROM metadata WHERE key LIKE ? AND key<? ORDER BY key DESC LIMIT ?",
                                ('audit:%', cursor or 'audit:~', limit + 1)).fetchall()
            return jsonify(events=[json.loads(row['value']) for row in rows[:limit]],
                           next_cursor=rows[limit-1]['key'] if len(rows) > limit else None)

    def record(self, action, resource, resource_id, details=None, actor=None):
        if actor is None:
            owner = getattr(g, 'owner', None)
            actor = {'type': 'owner', 'id': owner['id']} if owner else {'type': 'system'}
        # Callers explicitly supply only operational facts, never arbitrary request bodies.
        allowed = {'from', 'to', 'payment_status', 'deadline_enabled', 'payment_hours', 'section', 'code'}
        facts = {k: v for k, v in (details or {}).items() if k in allowed and type(v) in (str, int, bool, type(None))}
        key = f'audit:{time.time_ns():020d}:{secrets.token_hex(8)}'
        event = dict(id=key, at=int(time.time()), action=action, resource=resource,
                     resource_id=str(resource_id), actor=actor, details=facts)
        self.db().execute('INSERT INTO metadata(key,value) VALUES(?,?)', (key, json.dumps(event)))
        return event

    def order_events(self, order_id):
        field = "value::jsonb->>'resource_id'" if self.postgres else "json_extract(value,'$.resource_id')"
        resource = "value::jsonb->>'resource'" if self.postgres else "json_extract(value,'$.resource')"
        rows = self.db().execute(f"SELECT value FROM metadata WHERE key LIKE ? AND {resource}='order' AND {field}=? ORDER BY key DESC LIMIT 100", ('audit:%', order_id)).fetchall()
        return [json.loads(row['value']) for row in rows]
