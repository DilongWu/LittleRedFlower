"""Website login: existing ADMIN credentials, opaque revocable HttpOnly sessions."""
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

COOKIE = 'redflower_session'


class WebAuth:
    def __init__(self, config=None):
        self.cfg = dict(os.environ if config is None else config)
        self.origin = self.cfg.get('AUTH_PUBLIC_ORIGIN') or self.cfg.get('VOICE_PUBLIC_ORIGIN', '')
        self.local = self.cfg.get('VOICE_LOCAL_TEST') == '1'
        self.path = self.cfg.get('AUTH_DB_PATH', str(Path(__file__).resolve().parent.parent / 'storage/auth.sqlite3'))
        if self.origin:
            parsed = urlsplit(self.origin)
            if not (parsed.scheme == 'https' or (self.local and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1')) or parsed.path or parsed.query or parsed.fragment or not parsed.netloc or parsed.username or parsed.password:
                raise RuntimeError('AUTH_PUBLIC_ORIGIN must be an exact HTTPS origin')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS web_sessions (
                token TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS login_rates (key TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);''')
        os.chmod(self.path, 0o600)
        self.router = APIRouter()
        self.router.add_api_route('/api/login', self.login, methods=['POST'])
        self.router.add_api_route('/api/session', self.session, methods=['GET'])
        self.router.add_api_route('/api/logout', self.logout, methods=['POST'])

    @contextlib.contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def guard(self, request):
        expected = self.origin or str(request.base_url).rstrip('/')
        if request.headers.get('host') != urlsplit(expected).netloc or request.headers.get('origin') != expected:
            raise HTTPException(403, 'origin rejected')

    def require_user(self, request):
        token = request.cookies.get(COOKIE, '')
        if not token or len(token) > 128:
            raise HTTPException(401, '请先登录网站')
        with self.connect() as c:
            row = c.execute('SELECT username FROM web_sessions WHERE token=? AND expires>?',
                            (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            raise HTTPException(401, '登录已过期，请重新登录网站')
        return row[0]

    async def login(self, request: Request):
        self.guard(request)
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, 'JSON required')
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > 4096:
                raise HTTPException(413, 'request too large')
        try:
            data = json.loads(content)
            username, password = data['username'], data['password']
            if not isinstance(username, str) or not isinstance(password, str) or len(username) > 256 or len(password) > 256:
                raise ValueError()
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise HTTPException(400, 'invalid credentials format') from None
        now = time.time()
        allowed = True
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM web_sessions WHERE expires<=?', (now,))
            c.execute('DELETE FROM login_rates WHERE start<?', (now-3600,))
            for key, limit in [('global', 30), ('ip:'+request.client.host, 10)]:
                c.execute('INSERT INTO login_rates VALUES (?,?,0) ON CONFLICT(key) DO NOTHING', (key, now))
                c.execute('UPDATE login_rates SET start=?,count=0 WHERE key=? AND start<?', (now, key, now-60))
                c.execute('UPDATE login_rates SET count=count+1 WHERE key=?', (key,))
                allowed = c.execute('SELECT count FROM login_rates WHERE key=?', (key,)).fetchone()[0] <= limit and allowed
        if not allowed:
            raise HTTPException(429, '稍后再试')
        # Same credential sources and defaults as the original website login.
        good_user = hmac.compare_digest(username.encode(), self.cfg.get('ADMIN_USERNAME', 'admin').encode())
        good_password = hmac.compare_digest(password.encode(), self.cfg.get('ADMIN_PASSWORD', 'littleredfloweradmin').encode())
        if not (good_user and good_password):
            raise HTTPException(401, 'Invalid credentials')
        token = secrets.token_urlsafe(32)
        with self.connect() as c:
            # Rotate a previous session on login, preventing session fixation.
            c.execute('DELETE FROM web_sessions WHERE token=?', (hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest(),))
            c.execute('INSERT INTO web_sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), username, now+43200))
        response = JSONResponse({'status': 'success'})
        response.set_cookie(COOKIE, token, max_age=43200, httponly=True, secure=not self.local, samesite='strict', path='/')
        response.headers['Cache-Control'] = 'no-store'
        return response

    async def session(self, request: Request):
        return JSONResponse({'username': self.require_user(request)}, headers={'Cache-Control': 'no-store'})

    async def logout(self, request: Request):
        self.guard(request)
        with self.connect() as c:
            c.execute('DELETE FROM web_sessions WHERE token=?', (hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest(),))
        response = JSONResponse({'ok': True}, headers={'Cache-Control': 'no-store'})
        response.delete_cookie(COOKIE, path='/', secure=not self.local, httponly=True, samesite='strict')
        return response
