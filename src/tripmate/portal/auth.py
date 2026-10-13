"""Opaque HttpOnly browser sessions; provider tokens stay in server memory."""
import secrets
import time
from dataclasses import dataclass, field
from threading import RLock
from tripmate.operations.common import OperationsError


@dataclass
class Session:
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    access: str = ''
    refresh: str = ''
    token_expires: float = 0
    created: float = field(default_factory=time.time)
    touched: float = field(default_factory=time.time)
    user_id: str = ''
    lock: RLock = field(default_factory=RLock)


class Sessions:
    def __init__(self, cloud):
        self.cloud, self.items, self.lock = cloud, {}, RLock()

    def create(self, tokens=None):
        with self.lock:
            now = time.time()
            self.items = {k: v for k, v in self.items.items() if now-v.created<28800 and now-v.touched<3600}
            if len(self.items) >= 1000:
                raise OperationsError('RATE_LIMITED', 'Session capacity reached. Try again later.')
            sid, session = secrets.token_urlsafe(32), Session()
            if tokens:
                self._tokens(session, tokens)
            self.items[sid] = session
            return sid, session

    @staticmethod
    def _tokens(session, tokens):
        session.access = tokens['access_token']
        session.refresh = tokens['refresh_token']
        session.token_expires = time.time()+tokens.get('expires_in', 3600)

    def get(self, sid):
        with self.lock:
            session = self.items.get(sid)
            if not session or time.time()-session.created>=28800 or time.time()-session.touched>=3600:
                self.items.pop(sid, None)
                raise OperationsError('LOGIN_REQUIRED', 'Sign in to continue.')
            session.touched = time.time()
            return session

    def identity(self, session):
        with session.lock:
            if not session.access:
                raise OperationsError('LOGIN_REQUIRED', 'Sign in to continue.')
            if session.token_expires-time.time()<60:
                self._tokens(session, self.cloud.request('/auth/v1/token?grant_type=refresh_token', 'POST', {'refresh_token': session.refresh}))
            user = self.cloud.user(session.access)
            if not user.get('email_confirmed_at') or not user.get('id'):
                raise OperationsError('VERIFICATION_FAILED', 'Verify your email before accessing a portal.')
            if session.user_id and user['id'] != session.user_id:
                raise OperationsError('ACCESS_DENIED', 'Session identity changed. Sign in again.')
            session.user_id = user['id']
            profile = self.cloud.profile(user['id'])
            return {'id': user['id'], 'email': user.get('email', ''), **profile}

    def remove(self, sid):
        with self.lock:
            return self.items.pop(sid, None)


class RateLimit:
    def __init__(self):
        self.attempts, self.lock = {}, RLock()

    def check(self, key, limit=6, window=60):
        now = time.monotonic()
        with self.lock:
            self.attempts = {k: [t for t in v if now-t<window] for k, v in self.attempts.items() if any(now-t<window for t in v)}
            times = self.attempts.setdefault(key, [])
            if len(times) >= limit:
                raise OperationsError('RATE_LIMITED', 'Too many attempts. Wait before trying again.')
            times.append(now)
