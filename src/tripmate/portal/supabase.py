"""Server-only Supabase client. Never return provider bodies or credentials in errors."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from tripmate.operations.common import OperationsError

MAX_RESPONSE_BYTES = 4_000_000
# The private snapshot includes immutable case history, traces and command results.
# A small multi-account rehearsal already exceeds the ordinary provider-body cap.
MAX_SNAPSHOT_BYTES = 32_000_000


class Supabase:
    def __init__(self, url, public_key, secret_key):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('Use the HTTPS project URL from Supabase.')
        if not public_key or not secret_key or public_key == secret_key:
            raise ValueError('Configure separate Supabase publishable and server secret keys.')
        self.url, self.public_key, self.secret_key = url.rstrip('/'), public_key, secret_key

    @classmethod
    def from_env(cls):
        return cls(os.environ.get('SUPABASE_URL', ''), os.environ.get('SUPABASE_PUBLISHABLE_KEY', ''), os.environ.get('SUPABASE_SECRET_KEY', ''))

    def request(self, path, method='GET', body=None, token=None, admin=False):
        key = self.secret_key if admin else self.public_key
        headers = {'apikey': key, 'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        elif admin and key.startswith('eyJ'):
            headers['Authorization'] = 'Bearer ' + key
        data = json.dumps(body).encode() if body is not None else None
        attempts = 2 if admin and path == '/rest/v1/rpc/tripmate_snapshot' else 1
        for attempt in range(attempts):
            try:
                with urlopen(Request(self.url + path, data=data, headers=headers, method=method), timeout=15) as response:
                    limit = MAX_SNAPSHOT_BYTES if admin and path == '/rest/v1/rpc/tripmate_snapshot' else MAX_RESPONSE_BYTES
                    raw = response.read(limit + 1)
                    if len(raw) > limit:
                        raise OperationsError('CLOUD_UNAVAILABLE',
                            'The cloud response exceeds the supported demo size. Ask the project administrator '
                            'to review storage before retrying; no records were deleted.')
                    return json.loads(raw) if raw else None
            except HTTPError as exc:
                # Read only a stable code to classify conflicts. Do not expose provider errors.
                try:
                    code = json.loads(exc.read(8192)).get('code')
                except (ValueError, AttributeError):
                    code = None
                if code == '57014' and attempt + 1 < attempts:
                    # The cancelled snapshot is read-only; never replay a write.
                    continue
                if code == '57014' and attempts == 2:
                    raise OperationsError('CLOUD_UNAVAILABLE', 'Cloud records could not be read in time. Refresh before retrying; no success is claimed.') from None
                if code == '40001':
                    raise OperationsError('UNCONFIRMED_REQUEST', 'Another request changed the data. Reload before retrying.') from None
                if exc.code in (400, 401, 403, 422) and path.startswith('/auth/'):
                    raise OperationsError('AUTH_FAILED', 'Unable to verify this account. Check your credentials and email verification.') from None
                if exc.code == 429:
                    raise OperationsError('RATE_LIMITED', 'Too many attempts. Wait before trying again.') from None
                raise OperationsError('CLOUD_UNAVAILABLE', 'The cloud service could not complete this request. No success is claimed.') from None
            except OperationsError:
                raise
            except (URLError, TimeoutError, OSError, ValueError):
                raise OperationsError('CLOUD_UNAVAILABLE', 'The cloud service is unavailable. Try again later.') from None

    def rpc(self, name, body=None):
        return self.request('/rest/v1/rpc/' + name, 'POST', body or {}, admin=True)

    def user(self, token):
        return self.request('/auth/v1/user', token=token)

    def profile(self, actor):
        rows = self.request('/rest/v1/tripmate_accounts?' + urlencode({'user_id': 'eq.' + actor, 'select': '*'}), admin=True)
        if len(rows) != 1 or not rows[0]['active']:
            raise OperationsError('ACCESS_DENIED', 'This account does not have active portal access.')
        p = rows[0]
        return {'id': p['user_id'], 'role': p['role'], 'verified': True, 'membership': p['membership'], 'paidUntil': p['paid_until'], 'simulated': False}
