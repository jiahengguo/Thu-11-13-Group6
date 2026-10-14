"""HTTP boundary, account revocation, cross-role/owner access and cloud atomicity."""
import json
import threading
import time
import unittest
from copy import deepcopy
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from uuid import uuid4
from tripmate.portal.server import make_server
from tripmate.portal.repository import SupabaseOperationsRepository
from tripmate.operations.common import OperationsError


class FakeCloud:
    def __init__(self):
        self.accounts, self.tokens = {}, {}
        self.state = {'version': 0, 'records': [], 'traces': [], 'commands': []}
        self.fail_commit = False
        self.requests=[]

    def add(self, role='TRAVELLER', verified=True):
        actor=str(uuid4()); token='token-'+actor
        self.accounts[actor]={'id':actor,'role':role,'verified':verified,'membership':'FREE','paidUntil':None,'simulated':False,'active':True}
        self.tokens[token]=actor
        return actor,token

    def user(self, token):
        if token not in self.tokens:
            raise OperationsError('AUTH_FAILED','Invalid account.')
        actor=self.tokens[token]
        return {'id':actor,'email':actor+'@example.invalid','email_confirmed_at':'2026-10-13' if self.accounts[actor]['verified'] else None}

    def profile(self, actor):
        if actor not in self.accounts or not self.accounts[actor]['active']:
            raise OperationsError('ACCESS_DENIED','Inactive account.')
        return {k:v for k,v in self.accounts[actor].items() if k!='active'}

    def request(self,path,method='GET',body=None,token=None,admin=False):
        self.requests.append((path,body))
        if path.startswith('/auth/v1/token?grant_type=password'):
            selected=next((t for t,a in self.tokens.items() if body['email']==a+'@example.invalid'),None)
            if not selected or body['password']!='test-password-long':
                raise OperationsError('AUTH_FAILED','Invalid account.')
            return {'access_token':selected,'refresh_token':selected,'expires_in':3600}
        if path.startswith('/auth/v1/token?grant_type=refresh_token'):
            selected=body['refresh_token'];self.user(selected)
            return {'access_token':selected,'refresh_token':selected,'expires_in':3600}
        if path.startswith('/auth/v1/logout'):
            self.tokens.pop(token,None)
        elif path.startswith('/auth/v1/signup') or path.startswith('/auth/v1/recover'):
            return {}
        else:
            raise AssertionError('Unexpected provider request')

    def rpc(self,name,body=None):
        body=body or {}
        if name=='tripmate_snapshot':
            return deepcopy(self.state)
        if name=='tripmate_commit':
            if self.fail_commit:
                raise OperationsError('CLOUD_UNAVAILABLE','Injected cloud failure.')
            if body['expected_version']!=self.state['version']:
                raise OperationsError('UNCONFIRMED_REQUEST','Concurrent change.')
            new=deepcopy(self.state)
            for row in body['writes']:
                new['records']=[r for r in new['records'] if (r['kind'],r['id'])!=(row['kind'],row['id'])]+[row]
            new['traces']+=body['events']
            if body['command_entry']:
                new['commands'].append(body['command_entry'])
            new['version']+=1
            self.state=new
            return new['version']
        raise AssertionError('Unexpected RPC')


class Browser:
    def __init__(self,root):
        self.root=root;self.cookies=CookieJar();self.client=build_opener(HTTPCookieProcessor(self.cookies));self.csrf=''
    def call(self,path,body=None,headers=None):
        h={}
        if body is not None:
            h={'Content-Type':'application/json','Origin':self.root,'X-CSRF-Token':self.csrf}
        h.update(headers or {})
        req=Request(self.root+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            response=self.client.open(req)
        except HTTPError as exc:
            response=exc
        raw=response.read();content=response.headers.get('Content-Type','')
        value=json.loads(raw) if 'json' in content else raw.decode()
        return response.status,value,response.headers
    def start(self):
        status,data,headers=self.call('/api/session');self.csrf=data['csrf'];return status,data,headers
    def login(self,actor):
        self.start();result=self.call('/api/auth/login',{'email':actor+'@example.invalid','password':'test-password-long'})
        if result[0]==200:self.start()
        return result


class PortalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.cloud=FakeCloud();self.a,_=self.cloud.add();self.b,_=self.cloud.add();self.operator,_=self.cloud.add('OPERATOR');self.supplier,_=self.cloud.add('SUPPLIER');self.unverified,_=self.cloud.add(verified=False)
        self.server=make_server(self.cloud,port=0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.root='http://127.0.0.1:'+str(self.server.server_port)
        self.browser=Browser(self.root)

    def create_case(self):
        self.browser.login(self.a)
        intents=[{'caseType':'ROUTINE_ENQUIRY','fields':{'details':'Explain membership.'}}]
        status,intake,_=self.browser.call('/api/operations/intake',{'requestKey':str(uuid4()),'text':'Explain membership.','intents':intents})
        self.assertEqual(status,200)
        status,result,_=self.browser.call('/api/operations/confirm',{'requestKey':str(uuid4()),'intakeId':intake['id'],'revision':intake['revision'],'intents':intents,'confirmed':True})
        self.assertEqual(status,200)
        return result['caseIds'][0]

    def test_four_browsers_can_repeatedly_login_from_the_same_ip(self):
        from concurrent.futures import ThreadPoolExecutor
        actors = [self.a, self.b, self.supplier, self.operator]
        browsers = [Browser(self.root) for _ in actors]
        def debug_login(pair):
            browser, actor = pair
            for _ in range(3):
                self.assertEqual(browser.login(actor)[0], 200)
            status, data, _ = browser.call('/api/session')
            self.assertEqual(status, 200)
            self.assertEqual(data['user']['id'], actor)
            route = {'TRAVELLER': '/app', 'SUPPLIER': '/supplier', 'OPERATOR': '/admin'}[data['user']['role']]
            self.assertEqual(browser.call(route)[0], 200)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(debug_login, zip(browsers, actors)))
        for browser, actor in zip(browsers, actors):
            self.assertEqual(browser.call('/api/session')[1]['user']['id'], actor)

    def test_portal_sessions_have_no_fixed_online_count_limit(self):
        sessions = self.server.app.sessions
        first, original = sessions.create()
        for _ in range(1001):
            sessions.create()
        self.assertIs(sessions.get(first), original)
        self.assertEqual(len(sessions.items), 1002)

    def test_public_website_has_no_role_switcher_or_diagnostic_routes(self):
        status,page,_=self.browser.call('/');self.assertEqual(status,200);self.assertIn('Plan your trip',page);self.assertNotIn('Choose a simulation role',page)
        for path in ['/api/fixtures','/api/checks','/operations','/api/operations/status']:
            self.assertEqual(self.browser.call(path)[0],401)

    def test_real_login_rotates_session_and_tokens_are_never_returned(self):
        _,_,before=self.browser.start();old_cookie=before['Set-Cookie']
        status,data,headers=self.browser.login(self.a)
        self.assertEqual(status,200);self.assertEqual(data,{'portal':'/app'})
        self.assertNotEqual(old_cookie,headers['Set-Cookie']);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Lax',headers['Set-Cookie'])
        _,me,_=self.browser.call('/api/session');self.assertNotIn('access_token',json.dumps(me));self.assertNotIn('refresh_token',json.dumps(me));self.assertEqual(me['user']['id'],self.a)

    def test_role_specific_html_is_rejected_server_side(self):
        self.browser.login(self.a)
        self.assertEqual(self.browser.call('/app')[0],200)
        self.assertEqual(self.browser.call('/admin')[0],403);self.assertEqual(self.browser.call('/supplier')[0],403)
        self.browser=Browser(self.root);self.browser.login(self.supplier)
        status,page,_=self.browser.call('/supplier');self.assertEqual(status,200);self.assertIn('Partner portal',page);self.assertNotIn('Supplier applications',page)
        self.assertEqual(self.browser.call('/app')[0],403)
        self.browser=Browser(self.root);self.browser.login(self.operator)
        self.assertEqual(self.browser.call('/admin')[0],200)

    def test_unverified_and_inactive_users_cannot_enter(self):
        self.assertEqual(self.browser.login(self.unverified)[0],403)
        self.browser=Browser(self.root);self.browser.login(self.a);self.cloud.accounts[self.a]['active']=False
        self.assertEqual(self.browser.call('/app')[0],403)
        self.assertEqual(self.browser.call('/api/operations/cases')[0],403)

    def test_role_change_takes_effect_without_session_relogin(self):
        self.browser.login(self.a);self.cloud.accounts[self.a]['role']='SUPPLIER'
        self.assertEqual(self.browser.call('/app')[0],403);self.assertEqual(self.browser.call('/supplier')[0],200)

    def test_login_and_writes_require_csrf_and_exact_origin(self):
        self.browser.start();body={'email':self.a+'@example.invalid','password':'test-password-long'}
        self.assertEqual(self.browser.call('/api/auth/login',body,{'X-CSRF-Token':'forged'})[0],403)
        self.assertEqual(self.browser.call('/api/auth/login',body,{'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(self.browser.call('/api/session',headers={'Host':'attacker.invalid'})[0],403)

    def test_signup_does_not_accept_self_assigned_role_and_requires_strong_password(self):
        self.browser.start();body={'email':'new@example.invalid','password':'test-password-long','role':'OPERATOR'}
        self.assertEqual(self.browser.call('/api/auth/signup',body)[0],422)
        body.pop('role');body['password']='short';self.assertEqual(self.browser.call('/api/auth/signup',body)[0],422)
        self.assertFalse(self.cloud.requests)

    def test_other_traveller_cannot_read_case_traces_or_intake(self):
        case_id=self.create_case();other=Browser(self.root);other.login(self.b)
        for path in ['/api/operations/case?caseId=','/api/operations/traces?caseId=','/api/operations/history?caseId=']:
            self.assertEqual(other.call(path+case_id)[0],403)
        self.assertEqual(other.call('/api/operations/cases')[1]['cases'],[])
        self.assertEqual(other.call('/api/intakes')[1]['intakes'],[])

    def test_identity_headers_and_body_cannot_impersonate_operator(self):
        case_id=self.create_case()
        self.assertEqual(self.browser.call('/api/operations/session',{'identityId':self.operator})[0],403)
        request={'requestKey':str(uuid4()),'caseId':case_id,'revision':1,'decision':'TAKE_OVER','reason':'Forged role.'}
        self.assertEqual(self.browser.call('/api/operations/review',request,{'X-Ops-Session':self.operator})[0],403)
        request['requesterId']=self.operator;self.assertEqual(self.browser.call('/api/operations/review',request)[0],422)

    def test_supplier_request_type_cannot_be_submitted_by_traveller(self):
        self.browser.login(self.a)
        body={'requestKey':str(uuid4()),'text':'Offer','intents':[{'caseType':'OFFER','fields':{'details':'Offer'}}]}
        self.assertEqual(self.browser.call('/api/operations/intake',body)[0],403)

    def test_cloud_failure_does_not_commit_intake_or_trace(self):
        self.browser.login(self.a);self.cloud.fail_commit=True
        result=self.browser.call('/api/operations/intake',{'requestKey':'failed-save','text':'Service?','intents':[{'caseType':'ROUTINE_ENQUIRY','fields':{'details':'Service?'}}]})
        self.assertEqual(result[0],503);self.assertEqual(self.cloud.state['records'],[]);self.assertEqual(self.cloud.state['traces'],[])

    def test_routine_delivery_is_private_and_atomic_and_operator_can_deliver(self):
        case_id=self.create_case();status,view,_=self.browser.call('/api/operations/dispatch',{'requestKey':'dispatch','caseId':case_id,'revision':1});self.assertEqual(status,200);self.assertIsNone(view['response'])
        staff=Browser(self.root);staff.login(self.operator)
        staff_view=staff.call('/api/operations/case?caseId='+case_id)[1];self.assertTrue(staff_view['response'])
        status,result,_=staff.call('/api/operations/deliver',{'requestKey':'deliver','caseId':case_id,'revision':view['revision']});self.assertEqual(status,200);self.assertTrue(result['delivered'])
        final=self.browser.call('/api/operations/case?caseId='+case_id)[1];self.assertEqual(final['case']['status'],'CLOSED');self.assertTrue(final['response'])
        self.assertIsNone(final['review']);self.assertNotIn('membershipSnapshots',final)

    def test_logout_removes_session_and_rejects_reused_cookie(self):
        self.browser.login(self.a);old=list(self.browser.cookies)[0].value
        self.assertEqual(self.browser.call('/api/auth/logout',{})[0],200)
        self.assertEqual(self.browser.call('/api/operations/cases',headers={'Cookie':'tripmate_session='+old})[0],401)

    def test_invalid_callback_does_not_create_authenticated_session(self):
        self.browser.start()
        self.assertEqual(self.browser.call('/api/auth/callback',{'access_token':'forged','refresh_token':'forged','state':self.browser.csrf})[0],401)
        self.assertIsNone(self.browser.call('/api/session')[1]['user'])

    def test_email_callback_is_bound_to_the_browser_that_requested_it(self):
        self.browser.start()
        token=next(t for t,a in self.cloud.tokens.items() if a==self.a)
        self.assertEqual(self.browser.call('/api/auth/callback',{'access_token':token,'refresh_token':token,'state':'attacker-state'})[0],403)
        self.assertIsNone(self.browser.call('/api/session')[1]['user'])

    def test_provider_refresh_uses_server_tokens_and_reverifies_user(self):
        self.browser.login(self.a);sid=list(self.browser.cookies)[0].value;self.server.app.sessions.items[sid].token_expires=0
        self.assertEqual(self.browser.call('/api/operations/cases')[0],200)
        self.assertTrue(any('refresh_token' in p for p,_ in self.cloud.requests))

    def test_expired_session_is_rejected(self):
        self.browser.login(self.a);sid=list(self.browser.cookies)[0].value;self.server.app.sessions.items[sid].created=time.time()-28801
        self.assertEqual(self.browser.call('/api/operations/cases')[0],401)

    def test_login_rate_limit(self):
        self.browser.start()
        for _ in range(6):
            self.assertEqual(self.browser.call('/api/auth/login',{'email':'bad@example.invalid','password':'wrong'})[0],401)
        self.assertEqual(self.browser.call('/api/auth/login',{'email':'bad@example.invalid','password':'wrong'})[0],429)


class CloudRepositoryTests(unittest.TestCase):
    def test_atomic_idempotency_and_conflicting_request_keys(self):
        cloud=FakeCloud();repo=SupabaseOperationsRepository(cloud)
        def save(records):records.put('test','id',{'value':1});return {'done':True}
        self.assertEqual(repo.command('k','f',save),repo.command('k','f',lambda _:self.fail('Repeated callback')))
        self.assertEqual(cloud.state['version'],1)
        with self.assertRaises(OperationsError):repo.command('k','other',save)
    def test_compare_and_swap_rejects_stale_changes_without_partial_write(self):
        cloud=FakeCloud();repo=SupabaseOperationsRepository(cloud)
        with self.assertRaises(OperationsError):
            with repo.transaction() as records:
                records.put('test','id',{'value':1});cloud.state['version']+=1
        self.assertEqual(cloud.state['records'],[])
    def test_failed_callback_does_not_save(self):
        cloud=FakeCloud();repo=SupabaseOperationsRepository(cloud)
        with self.assertRaises(RuntimeError):
            with repo.transaction() as records:
                records.put('test','id',{});raise RuntimeError()
        self.assertEqual(cloud.state['version'],0)
    def test_request_cache_is_isolated_and_invalidated_after_commit(self):
        cloud=FakeCloud();repo=SupabaseOperationsRepository(cloud)
        with repo.scope():
            self.assertEqual(repo.list('test'),[])
            with repo.transaction() as records:records.put('test','id',{'value':1})
            self.assertEqual(repo.read('test','id'),{'value':1})
        cloud.state['records'][0]['payload']={'value':2}
        with repo.scope():self.assertEqual(repo.read('test','id'),{'value':2})
    def test_external_bind_requires_https_and_local_http_requires_loopback(self):
        with self.assertRaises(ValueError):make_server(FakeCloud(),bind='0.0.0.0')
        with self.assertRaises(ValueError):make_server(FakeCloud(),origin='http://example.com',bind='0.0.0.0')
        with self.assertRaises(ValueError):make_server(FakeCloud(),origin='http://localhost:8780',bind='0.0.0.0')


if __name__=='__main__':unittest.main()
