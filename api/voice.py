"""Single-instance outbound relay authenticated by the website session."""
import contextlib
import logging
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


def create_voice_app(config=None, auth=None):
    cfg = dict(os.environ if config is None else config)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    enabled = cfg.get('VOICE_ENABLED') == '1'
    origin = cfg.get('VOICE_PUBLIC_ORIGIN', '')
    local = cfg.get('VOICE_LOCAL_TEST') == '1'
    worker_secret = cfg.get('VOICE_WORKER_SECRET', '')
    db_path = cfg.get('VOICE_DB_PATH', '')
    lock = None
    owner_pid = os.getpid()
    if enabled:
        try:
            import fcntl
        except ImportError:
            raise RuntimeError('Voice requires Linux file locking') from None
        parsed = urlsplit(origin)
        if not (parsed.scheme == 'https' or (local and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1')) or parsed.path or parsed.query or parsed.fragment or not parsed.netloc or parsed.username or parsed.password:
            raise RuntimeError('Voice requires an exact HTTPS origin')
        if auth is None or len(worker_secret) < 32 or not worker_secret.isascii():
            raise RuntimeError('Website auth and independent strong worker credential required')
        if hmac.compare_digest(worker_secret.encode(), auth.cfg.get('ADMIN_PASSWORD', 'littleredfloweradmin').encode()):
            raise RuntimeError('Worker credential must differ from website password')
        if auth.origin != origin:
            raise RuntimeError('Website and voice must share the same public origin')
        if cfg.get('VOICE_SINGLE_INSTANCE') != '1' or cfg.get('VOICE_INSTANCE_COUNT') != '1' or cfg.get('WEB_CONCURRENCY', '1') != '1':
            raise RuntimeError('Voice SQLite requires explicitly verified single instance / single worker')
        if not os.path.isabs(db_path):
            raise RuntimeError('VOICE_DB_PATH must be an absolute persistent path')
        Path(db_path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = open(db_path + '.lock', 'a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            raise RuntimeError('Another voice process already owns this store') from None

    @contextlib.contextmanager
    def db():
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('BEGIN IMMEDIATE')
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    if enabled:
        with db() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS rates (key TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, user TEXT NOT NULL, idem TEXT NOT NULL, text TEXT NOT NULL,
                  state TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
                  lease TEXT, reply TEXT, UNIQUE(user, idem));
            ''')
        os.chmod(db_path, 0o600)
    app.state.voice_lock = lock  # Keep lifetime ownership; process exit releases flock.

    def expire(c, now):
        c.execute("UPDATE jobs SET state='expired',text='',reply=NULL WHERE expires<=? AND state IN ('queued','leased','running')", (now,))
        c.execute('DELETE FROM rates WHERE start<?', (now-3600,))
        # Bounded retention; old UUID keys cannot execute again after deletion (see submission age check).
        c.execute('DELETE FROM jobs WHERE created<?', (now-86400,))

    def rate(c, key, limit, window=60):
        now = time.time()
        c.execute('INSERT INTO rates VALUES (?,?,0) ON CONFLICT(key) DO NOTHING', (key, now))
        c.execute('UPDATE rates SET start=?,count=0 WHERE key=? AND start<?', (now, key, now-window))
        c.execute('UPDATE rates SET count=count+1 WHERE key=?', (key,))
        return c.execute('SELECT count FROM rates WHERE key=?', (key,)).fetchone()[0] <= limit

    def user(request, c):
        return auth.require_user(request)

    def worker(request):
        value = request.headers.get('authorization', '')
        if not hmac.compare_digest(value.encode(), ('Bearer ' + worker_secret).encode()):
            raise HTTPException(401, 'worker authentication required')

    async def body(request):
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, 'JSON required')
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > 24000:
                raise HTTPException(413, 'request too large')
        try:
            value = json.loads(chunks)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise HTTPException(400, 'invalid JSON') from None

    @app.middleware('http')
    async def guard(request, call_next):
        if enabled and os.getpid() != owner_pid:
            return JSONResponse({'detail': 'preloaded multi-process voice deployment rejected'}, status_code=503)
        if not enabled:
            return JSONResponse({'detail': 'voice disabled'}, status_code=404)
        # Fixed deployment origin, never derived from untrusted Forwarded/Host headers.
        if request.headers.get('host') != urlsplit(origin).netloc:
            return JSONResponse({'detail': 'host rejected'}, status_code=403)
        is_worker = request.url.path.startswith(request.scope.get('root_path', '') + '/worker/')
        if not is_worker and request.method not in ('GET', 'HEAD') and request.headers.get('origin') != origin:
            return JSONResponse({'detail': 'origin rejected'}, status_code=403)
        if request.headers.get('origin') and request.headers['origin'] != origin:
            return JSONResponse({'detail': 'origin rejected'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/status')
    async def status(request: Request):
        with db() as c:
            user(request, c)
        return {'backend': 'private outbound relay', 'mode': 'half-duplex'}

    @app.post('/jobs')
    async def submit(request: Request):
        data = await body(request)
        text, idem, issued = data.get('text'), data.get('idempotencyKey'), data.get('issuedAt')
        now = time.time()
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000 or not isinstance(idem, str) or not 16 <= len(idem) <= 80:
            raise HTTPException(400, 'invalid text / idempotency key')
        if isinstance(issued, bool) or not isinstance(issued, (float, int)) or not now-30 <= issued <= now+5:
            raise HTTPException(409, 'stale submission; do not automatically resend')
        with db() as c:
            uid = user(request, c)
            expire(c, now)
            old = c.execute('SELECT * FROM jobs WHERE user=? AND idem=?', (uid, idem)).fetchone()
            if old:
                if old['text'] and old['text'] != text.strip():
                    raise HTTPException(409, 'idempotency conflict')
                return {'id': old['id'], 'state': old['state']}
            allowed = rate(c, 'submit:'+uid, 12)
            busy = c.execute("SELECT 1 FROM jobs WHERE state IN ('queued','leased','running')").fetchone()
            if allowed and not busy:
                jid = secrets.token_urlsafe(24)
                c.execute('INSERT INTO jobs (id,user,idem,text,state,created,expires) VALUES (?,?,?,?,?,?,?)', (jid, uid, idem, text.strip(), 'queued', now, now+30))
        if not allowed:
            raise HTTPException(429, 'too many requests')
        if busy:
            raise HTTPException(409, '白总正在回答，请稍候')
        return {'id': jid, 'state': 'queued'}

    @app.get('/jobs/{jid}')
    async def poll(jid: str, request: Request):
        with db() as c:
            uid = user(request, c)
            expire(c, time.time())
            row = c.execute('SELECT state,reply FROM jobs WHERE id=? AND user=?', (jid, uid)).fetchone()
        if not row:
            raise HTTPException(404, 'job not found')
        return dict(row)

    @app.post('/jobs/{jid}/cancel')
    async def cancel(jid: str, request: Request):
        with db() as c:
            uid = user(request, c)
            row = c.execute('SELECT state FROM jobs WHERE id=? AND user=?', (jid, uid)).fetchone()
            if not row:
                raise HTTPException(404, 'job not found')
            c.execute("UPDATE jobs SET state='cancelled',text='',reply=NULL WHERE id=? AND state IN ('queued','leased','running')", (jid,))
        return {'ok': True, 'warning': '已开始的白总操作可能继续执行，请先确认结果。'}

    @app.post('/worker/claim')
    async def claim(request: Request):
        worker(request)
        now = time.time()
        with db() as c:
            expire(c, now)
            row = c.execute("SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:
                return {'job': None}
            lease = secrets.token_urlsafe(32)
            c.execute("UPDATE jobs SET state='leased',lease=?,expires=? WHERE id=?", (lease, now+10, row['id']))
        return {'job': {'id': row['id'], 'lease': lease}}

    @app.post('/worker/{jid}/start')
    async def start(jid: str, request: Request):
        worker(request)
        data = await body(request)
        if not isinstance(data.get('lease'), str) or len(data['lease']) > 128:
            raise HTTPException(400, 'invalid lease')
        now = time.time()
        with db() as c:
            expire(c, now)
            row = c.execute("SELECT text FROM jobs WHERE id=? AND lease=? AND state='leased' AND expires>?", (jid, data.get('lease'), now)).fetchone()
            if row:
                c.execute("UPDATE jobs SET state='running',expires=? WHERE id=?", (now+130, jid))
        if not row:
            raise HTTPException(409, 'lease expired or already started; never dispatch again')
        return {'text': row['text'], 'dispatchBefore': now+3, 'expires': now+130}

    @app.post('/worker/{jid}/result')
    async def result(jid: str, request: Request):
        worker(request)
        data = await body(request)
        if not isinstance(data.get('lease'), str) or len(data['lease']) > 128:
            raise HTTPException(400, 'invalid lease')
        reply = data.get('reply')
        if not isinstance(reply, str) or not 1 <= len(reply) <= 6000 or data.get('state') not in ('done', 'failed'):
            raise HTTPException(400, 'invalid result')
        with db() as c:
            expire(c, time.time())
            row = c.execute('SELECT state FROM jobs WHERE id=? AND lease=?', (jid, data.get('lease'))).fetchone()
            if row and row['state'] == 'running':
                c.execute('UPDATE jobs SET state=?,reply=?,text=? WHERE id=?', (data['state'], reply, '', jid))
            elif not row or row['state'] not in ('done', 'failed'):
                raise HTTPException(409, 'job expired')
        return {'ok': True}

    return app


def load_voice_app(config=None, auth=None):
    """Fail closed for optional voice, without disabling the finance website."""
    try:
        return create_voice_app(config, auth=auth)
    except (RuntimeError, OSError, sqlite3.Error):
        logging.getLogger(__name__).error('Voice disabled: deployment validation/storage failed; see docs/VOICE.md')
        return create_voice_app({'VOICE_ENABLED': '0'}, auth=auth)
