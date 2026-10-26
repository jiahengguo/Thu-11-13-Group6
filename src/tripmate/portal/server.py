"""Supabase-backed portals. Run behind an HTTPS reverse proxy for deployment."""
import argparse
import json
import os
import secrets
from functools import wraps
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, quote
from tripmate.api.settings import Settings
from tripmate.api.server import Workbench
from tripmate.operations import OperationsService
from tripmate.operations.common import OperationsError, safe_text
from tripmate.planning.common import PlanningError
from .auth import Sessions, RateLimit
from .repository import SupabaseOperationsRepository, NoUserFixtures
from .supabase import Supabase

PORTALS = {'TRAVELLER': '/app', 'SUPPLIER': '/supplier', 'OPERATOR': '/admin'}
COOKIE = 'tripmate_session'


class Portal:
    def __init__(self, cloud, supplier_pricing=None, supplier_policy=None):
        self.cloud, self.sessions, self.rate = cloud, Sessions(cloud), RateLimit()
        self.operations = OperationsService(SupabaseOperationsRepository(cloud), NoUserFixtures(), seed_profiles=False)
        if os.environ.get('ELEC5620_API_KEY') not in (None, '', 'REPLACE_LOCALLY'):
            try:
                from tripmate.adapters.campus import CampusLLMService
                self.operations.llm = CampusLLMService(timeout=20)
            except (ImportError, ValueError):
                pass
        from tripmate.supplier.gateway import SupplierGateway
        from tripmate.fixtures.shared import SharedFixtureCatalog
        self.supplier = SupplierGateway(self.operations, supplier_pricing, supplier_policy)
        self.fixtures = SharedFixtureCatalog(self.operations.repository)
        from tripmate.operations.integration import connect_planning
        from tripmate.planning.shared_repository import SharedPlanningRepository
        from tripmate.planning.review import planning_reviewer
        self.planning = SharedPlanningRepository(self.operations.repository)
        connect_planning(self.operations, self.supplier, planning_reviewer(self.operations, self.supplier), self.planning)

    def ops_actor(self, actor):
        return actor  # Only Handler's verified server identity can reach this adapter.

    def operation(self, action, body, identity):
        if action == 'session':
            raise OperationsError('ACCESS_DENIED', 'Simulated identity selection is disabled.')
        return Workbench.ops_post(self, action, body, identity['id'])

    _save_analysis = staticmethod(Workbench._save_analysis)


def make_server(cloud, port=8780, origin=None, bind='127.0.0.1', supplier_pricing=None, supplier_policy=None):
    app, static = Portal(cloud, supplier_pricing, supplier_policy), Path(__file__).with_name('static')
    configured_origin = origin
    if origin:
        p = urlsplit(origin)
        if p.scheme not in ('http', 'https') or p.path not in ('', '/') or p.query or p.fragment or p.username:
            raise ValueError('Set one exact public origin, without a path.')
        if p.scheme != 'https' and p.hostname not in ('127.0.0.1', 'localhost'):
            raise ValueError('Public deployments require HTTPS.')
        if p.hostname in ('127.0.0.1', 'localhost') and bind not in ('127.0.0.1', 'localhost'):
            raise ValueError('Local HTTP must bind only to loopback.')
    elif bind != '127.0.0.1':
        raise ValueError('Configure an HTTPS public origin before binding externally.')

    def request_scope(method):
        @wraps(method)
        def wrapped(handler):
            with app.operations.repository.scope():
                return method(handler)
        return wrapped

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        @property
        def origin(self):
            return (configured_origin or f'http://127.0.0.1:{self.server.server_port}').rstrip('/')

        def cookie(self, sid):
            return f'{COOKIE}={sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800' + ('; Secure' if self.origin.startswith('https:') else '')

        def sid(self):
            try:
                cookies = SimpleCookie(self.headers.get('Cookie', ''))
                return cookies[COOKIE].value if COOKIE in cookies else ''
            except Exception:
                return ''

        def send(self, status, payload, mime='application/json; charset=utf-8', sid=None, location=None):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            for name, value in {'Content-Type': mime, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'", 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'}.items():
                self.send_header(name, value)
            if self.origin.startswith('https:'):
                self.send_header('Strict-Transport-Security', 'max-age=31536000')
            if sid is not None:
                self.send_header('Set-Cookie', self.cookie(sid))
            if location:
                self.send_header('Location', location)
            self.end_headers()
            self.wfile.write(raw)

        def identity(self):
            return app.sessions.identity(app.sessions.get(self.sid()))

        def boundary(self, write=False):
            if self.headers.get('Host') != urlsplit(self.origin).netloc:
                raise OperationsError('ACCESS_DENIED', 'Unexpected request host.')
            if write and self.headers.get('Origin') != self.origin:
                raise OperationsError('ACCESS_DENIED', 'Submit requests from the same website.')

        def failure(self, exc):
            code = exc.code
            status = 401 if code in ('LOGIN_REQUIRED', 'AUTH_FAILED') else 403 if code in ('ACCESS_DENIED','VERIFICATION_FAILED') else 429 if code == 'RATE_LIMITED' else 503 if code == 'CLOUD_UNAVAILABLE' else 409 if code == 'UNCONFIRMED_REQUEST' else 422
            return self.send(status, {'error': code, 'message': str(exc)})

        @request_scope
        def do_GET(self):
            try:
                self.boundary()
                path, query = urlsplit(self.path).path, parse_qs(urlsplit(self.path).query)
                assets = {'/': ('home.html','text/html; charset=utf-8'), '/login': ('login.html','text/html; charset=utf-8'), '/auth/callback': ('login.html','text/html; charset=utf-8'), '/portal.css': ('portal.css','text/css; charset=utf-8'), '/auth.js': ('auth.js','text/javascript; charset=utf-8'), '/portal.js': ('portal.js','text/javascript; charset=utf-8')}
                if path in assets:
                    name,mime=assets[path]
                    return self.send(200,(static/name).read_bytes(),mime)
                if path in PORTALS.values():
                    try:
                        user = self.identity()
                    except OperationsError as exc:
                        if exc.code in ('LOGIN_REQUIRED','AUTH_FAILED'):
                            return self.send(303,b'',location='/login')
                        raise
                    if PORTALS[user['role']] != path:
                        raise OperationsError('ACCESS_DENIED', 'This account cannot access this portal.')
                    return self.send(200,(static/(user['role'].lower()+'.html')).read_bytes(),'text/html; charset=utf-8')
                if path == '/api/session':
                    sid=self.sid()
                    try:
                        session=app.sessions.get(sid)
                    except OperationsError:
                        app.rate.check(('session',self.client_address[0]),limit=30)
                        sid,session=app.sessions.create()
                    user=app.sessions.identity(session) if session.access else None
                    return self.send(200,{'user':user,'csrf':session.csrf,'portal':PORTALS[user['role']] if user else None},sid=sid)
                user=self.identity()
                actor=user['id']
                if path == '/api/supplier/assessment' and set(query) == {'caseId'} and len(query['caseId']) == 1:
                    return self.send(200, app.supplier.view(actor, query['caseId'][0]))
                if path == '/api/demo/fixtures' and not query:
                    if user['role'] != 'OPERATOR':
                        raise OperationsError('ACCESS_DENIED', 'Only operators can inspect the shared simulation catalog.')
                    return self.send(200, app.fixtures.summary())
                if path == '/api/operations/cases' and not query:
                    return self.send(200,{'cases':app.operations.cases(actor)})
                if path == '/api/trips' and not query and user['role']=='TRAVELLER':
                    return self.send(200,{'trips':app.operations.trips(actor)})
                if path == '/api/intakes' and not query and user['role']!='OPERATOR':
                    return self.send(200,{'intakes':[r for r in app.operations.repository.list('intake') if r['requesterId']==actor and not r['caseIds']]})
                if path in ('/api/operations/case','/api/operations/traces','/api/operations/history') and set(query)=={'caseId'} and len(query['caseId'])==1:
                    case_id=query['caseId'][0]
                    if path.endswith('/case'):
                        result=app.operations.case_view(actor,case_id)
                    elif path.endswith('/history'):
                        result={'history':app.operations.history(actor,case_id)}
                    else:
                        result={'events':app.operations.traces(actor,case_id)}
                    return self.send(200,result)
                if path == '/api/operations/plan' and set(query)=={'versionId'} and len(query['versionId'])==1:
                    return self.send(200,app.operations.plan_view(actor,query['versionId'][0]))
                if path == '/api/partners' and not query and user['role'] in ('TRAVELLER','OPERATOR'):
                    return self.send(200,{'applications':app.cloud.rpc('tripmate_partner_list',{'actor':actor})})
                return self.send(404,{'error':'NOT_FOUND'})
            except (OperationsError, PlanningError) as exc:
                return self.failure(exc)
            except Exception:
                return self.send(503,{'error':'SERVICE_UNAVAILABLE','message':'Unable to load this page. Try again later.'})

        @request_scope
        def do_POST(self):
            try:
                self.boundary(write=True)
                session=app.sessions.get(self.sid())
                if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),session.csrf):
                    raise OperationsError('ACCESS_DENIED','Reload the page before submitting.')
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    return self.send(415,{'error':'JSON_REQUIRED'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=16384:
                        return self.send(413,{'error':'BODY_SIZE_INVALID'})
                    self.connection.settimeout(10)
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):
                        raise ValueError()
                except (ValueError,OSError):
                    return self.send(400,{'error':'INVALID_JSON'})
                path=urlsplit(self.path).path
                if path in ('/api/auth/login','/api/auth/signup','/api/auth/recover'):
                    app.rate.check(('auth-ip',self.client_address[0]),limit=60)
                    app.rate.check(('auth-session',session.csrf))
                    required={'email'} if path.endswith('recover') else {'email','password'}
                    if set(body)!=required or not isinstance(body.get('email'),str) or not 3<=len(body['email'])<=254 or '@' not in body['email']:
                        raise OperationsError('INVALID_CONTRACT','Enter a valid email and the required credentials.')
                    if 'password' in body and (not isinstance(body['password'],str) or not 1<=len(body['password'])<=128):
                        raise OperationsError('INVALID_CONTRACT','Enter your password.')
                    if path.endswith('signup'):
                        if len(body['password'])<12:
                            raise OperationsError('INVALID_CONTRACT','Use a password with at least 12 characters.')
                        callback=self.origin+'/auth/callback?state='+session.csrf
                        app.cloud.request('/auth/v1/signup?redirect_to='+quote(callback,safe=''),'POST',body)
                        return self.send(200,{'message':'If registration is available, check your email to confirm your account, then sign in.'})
                    if path.endswith('recover'):
                        callback=self.origin+'/auth/callback?state='+session.csrf
                        app.cloud.request('/auth/v1/recover?redirect_to='+quote(callback,safe=''),'POST',body)
                        return self.send(200,{'message':'If this account exists, check your email for recovery instructions.'})
                    tokens=app.cloud.request('/auth/v1/token?grant_type=password','POST',body)
                    new_sid,new_session=app.sessions.create(tokens)
                    try:
                        user=app.sessions.identity(new_session)
                    except Exception:
                        app.sessions.remove(new_sid)
                        raise
                    app.sessions.remove(self.sid())
                    return self.send(200,{'portal':PORTALS[user['role']]},sid=new_sid)
                if path == '/api/auth/callback':
                    app.rate.check(('auth-ip',self.client_address[0]),limit=60)
                    app.rate.check(('auth-session',session.csrf))
                    if set(body)!={'access_token','refresh_token','state'} or any(not isinstance(v,str) or not 1<=len(v)<=8192 for v in body.values()):
                        raise OperationsError('INVALID_CONTRACT','Invalid sign-in link. Request a new email link.')
                    if not secrets.compare_digest(body['state'],session.csrf):
                        raise OperationsError('ACCESS_DENIED','Open this email link in the browser that requested it. You can also sign in after verifying your email.')
                    new_sid,new_session=app.sessions.create({'access_token':body['access_token'],'refresh_token':body['refresh_token'],'expires_in':0})
                    try:
                        user=app.sessions.identity(new_session)
                    except Exception:
                        app.sessions.remove(new_sid)
                        raise
                    app.sessions.remove(self.sid())
                    return self.send(200,{'portal':PORTALS[user['role']]},sid=new_sid)
                if path == '/api/auth/password':
                    app.sessions.identity(session)
                    if set(body)!={'password'} or not isinstance(body['password'],str) or not 12<=len(body['password'])<=128:
                        raise OperationsError('INVALID_CONTRACT','Use a password with 12 to 128 characters.')
                    app.cloud.request('/auth/v1/user','PUT',body,token=session.access)
                    app.sessions.remove(self.sid())
                    return self.send(200,{'message':'Password updated. Sign in with your new password.'},sid='')
                if path == '/api/auth/logout':
                    app.sessions.remove(self.sid())
                    if session.access:
                        try:
                            app.cloud.request('/auth/v1/logout?scope=local','POST',{},token=session.access)
                        except OperationsError:
                            pass
                    return self.send(200,{'message':'Signed out.'},sid='')
                user=app.sessions.identity(session)
                app.rate.check(('write',user['id']),limit=60)
                if path in ('/api/supplier/review', '/api/supplier/decision'):
                    return self.send(200, app.supplier.mutate(user['id'], path.rsplit('/', 1)[1], body))
                if path == '/api/demo/fixtures/reset':
                    if user['role'] != 'OPERATOR' or body:
                        raise OperationsError('ACCESS_DENIED', 'Only operators can reset the isolated simulation catalog.')
                    return self.send(200, app.fixtures.reset())
                if path.startswith('/api/operations/'):
                    return self.send(200,app.operation(path.removeprefix('/api/operations/'),body,user))
                if path == '/api/partners/apply' and user['role']=='TRAVELLER' and set(body)=={'company','description'}:
                    return self.send(200,app.cloud.rpc('tripmate_partner_apply',{'actor':user['id'],'company_name':safe_text(body['company'],160),'description_text':safe_text(body['description'],2000)}))
                if path == '/api/partners/review' and user['role']=='OPERATOR' and set(body)=={'applicant','decision','reason'}:
                    from uuid import UUID
                    try:
                        applicant=str(UUID(body['applicant']))
                    except (ValueError,TypeError,AttributeError):
                        raise OperationsError('INVALID_CONTRACT','Choose a valid applicant.')
                    if body['decision'] not in ('APPROVED','REJECTED'):
                        raise OperationsError('INVALID_CONTRACT','Choose Approve or Reject.')
                    return self.send(200,app.cloud.rpc('tripmate_partner_review',{'actor':user['id'],'applicant':applicant,'decision':body['decision'],'review_reason':safe_text(body['reason'],1000)}))
                return self.send(404,{'error':'NOT_FOUND'})
            except (OperationsError, PlanningError) as exc:
                return self.failure(exc)
            except Exception:
                return self.send(503,{'error':'SERVICE_UNAVAILABLE','message':'The action could not complete. Reload before retrying.'})

    server=ThreadingHTTPServer((bind,port),Handler)
    server.app=app
    return server


def main():
    parser=argparse.ArgumentParser(description='TripMate authenticated Supabase portals')
    parser.add_argument('--port',type=int,default=8780)
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--env-file',type=Path,default=Path('.env'))
    parser.add_argument('--demo-pricing',action='store_true',
                        help='Use explicit simulated pricing: 10%% markup, AUD 15 minimum margin; not a production policy')
    args=parser.parse_args()
    Settings.load(args.env_file)
    cloud=Supabase.from_env()
    cloud.rpc('tripmate_snapshot')  # Fail startup clearly if migration/credentials are missing.
    from tripmate.supplier.common import PricingPolicy
    policy = PricingPolicy('0.10', '15.00', 'demo-2026-10-24') if args.demo_pricing else None
    server=make_server(cloud,args.port,os.environ.get('TRIPMATE_PUBLIC_ORIGIN'),args.bind,supplier_policy=policy)
    print(f'TripMate portals | http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=='__main__':
    main()
