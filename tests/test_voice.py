"""Run: python3 -m unittest tests.test_voice -v (isolated, no finance imports)."""
import sqlite3
import tempfile
import time
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.voice import create_voice_app, load_voice_app
from api.auth import WebAuth, COOKIE


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = self.temp.name+'/voice.db'
        self.cfg = dict(VOICE_ENABLED='1', VOICE_PUBLIC_ORIGIN='https://voice.example',
                        AUTH_DB_PATH=self.temp.name+'/auth.db', ADMIN_USERNAME='owner', ADMIN_PASSWORD='test-password', VOICE_WORKER_SECRET='worker-test-'+'s'*40,
                        VOICE_SINGLE_INSTANCE='1', VOICE_INSTANCE_COUNT='1', VOICE_DB_PATH=self.path)
        self.auth = WebAuth(self.cfg)
        self.voice = create_voice_app(self.cfg, auth=self.auth)
        self.app = FastAPI()
        self.app.include_router(self.auth.router)
        self.app.mount('/api/voice', self.voice)
        self.client = TestClient(self.app, base_url='https://voice.example')
        self.headers = {'Origin':'https://voice.example'}
        self.worker = {'Authorization':'Bearer '+self.cfg['VOICE_WORKER_SECRET']}

    def tearDown(self):
        self.client.close()
        self.voice.state.voice_lock.close()
        self.temp.cleanup()

    def post(self, path, data=None, worker=False):
        return self.client.post('/api/voice'+path, json=data or {}, headers=self.worker if worker else self.headers)

    def login(self):
        r=self.client.post('/api/login', json={'username':'owner','password':'test-password'}, headers=self.headers)
        self.assertEqual(r.status_code,200)
        self.assertIn('HttpOnly',r.headers['set-cookie'])
        self.assertIn('Secure',r.headers['set-cookie'])

    def submit(self, key='test-idempotency-key', text='你好'):
        return self.post('/jobs', {'text':text,'idempotencyKey':key,'issuedAt':time.time()})

    def start(self, jid):
        lease=self.post('/worker/claim',worker=True).json()['job']
        self.assertEqual(lease['id'],jid)
        started=self.post('/worker/'+jid+'/start',{'lease':lease['lease']},True)
        self.assertEqual(started.status_code,200)
        return lease['lease']

    def test_default_disabled_and_configuration_fail_closed(self):
        disabled=TestClient(create_voice_app({}))
        self.assertEqual(disabled.get('/status').status_code,404)
        for changes in ({'VOICE_WORKER_SECRET':'short'},{'VOICE_INSTANCE_COUNT':'2'},{'WEB_CONCURRENCY':'2'},{'VOICE_PUBLIC_ORIGIN':'http://voice.example'},{'VOICE_DB_PATH':'relative'}):
            with self.assertRaises(RuntimeError):create_voice_app({**self.cfg,**changes},auth=self.auth)
        with self.assertRaises(RuntimeError):create_voice_app(self.cfg,auth=self.auth)

    def test_auth_origin_host_and_legacy_token_rejected(self):
        self.client.cookies.set('auth_token','valid_token_from_server')
        self.assertEqual(self.submit().status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'username':'owner','password':'test-password'}).status_code,403)
        self.assertEqual(self.client.post('/api/login',json={'username':'owner','password':'test-password'},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/voice/status',headers={'Host':'evil.example'}).status_code,403)
        self.login()
        self.assertEqual(self.post('/worker/claim').status_code,401)
        self.assertEqual(self.client.post('/api/logout',headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/voice/status').status_code,401)

    def test_lifecycle_idempotency_and_no_second_dispatch(self):
        self.login()
        job=self.submit().json()
        self.assertEqual(self.submit().json()['id'],job['id'])
        self.assertEqual(self.submit(text='different').status_code,409)
        self.assertEqual(self.submit('another-idempotency-key').status_code,409)
        lease=self.start(job['id'])
        self.assertEqual(self.post('/worker/'+job['id']+'/start',{'lease':lease},True).status_code,409)
        self.assertIsNone(self.post('/worker/claim',worker=True).json()['job'])
        result={'lease':lease,'state':'done','reply':'你好，车主'}
        self.assertEqual(self.post('/worker/'+job['id']+'/result',result,True).status_code,200)
        self.assertEqual(self.post('/worker/'+job['id']+'/result',result,True).status_code,200)
        self.assertEqual(self.client.get('/api/voice/jobs/'+job['id']).json()['reply'],'你好，车主')
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT text FROM jobs').fetchone()[0],'')
        with sqlite3.connect(self.cfg['AUTH_DB_PATH']) as c:
            self.assertNotEqual(c.execute('SELECT token FROM web_sessions').fetchone()[0],self.client.cookies[COOKIE])
            c.execute("UPDATE web_sessions SET username='other-user'")
        self.assertEqual(self.client.get('/api/voice/jobs/'+job['id']).status_code,404)

    def test_expiry_no_requeue_and_stale_input(self):
        self.login()
        stale=self.post('/jobs',{'text':'hello','idempotencyKey':'test-expired-request','issuedAt':time.time()-60})
        self.assertEqual(stale.status_code,409)
        jid=self.submit().json()['id']
        lease=self.post('/worker/claim',worker=True).json()['job']['lease']
        with sqlite3.connect(self.path) as c:c.execute('UPDATE jobs SET expires=?',(time.time()-1,))
        self.assertEqual(self.post('/worker/'+jid+'/start',{'lease':lease},True).status_code,409)
        self.assertIsNone(self.post('/worker/claim',worker=True).json()['job'])
        self.assertEqual(self.client.get('/api/voice/jobs/'+jid).json()['state'],'expired')

    def test_login_throttle_and_input_bounds(self):
        for _ in range(10):
            self.assertEqual(self.client.post('/api/login',json={'username':'owner','password':'wrong'},headers=self.headers).status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'username':'owner','password':'test-password'},headers=self.headers).status_code,429)
        self.assertEqual(self.client.post('/api/login',content='x'*5000,headers={**self.headers,'Content-Type':'application/json'}).status_code,413)

    def test_website_session_expiry_and_cancel(self):
        self.login()
        self.assertEqual(self.client.get('/api/session').status_code,200)
        jid=self.submit().json()['id']
        lease=self.post('/worker/claim',worker=True).json()['job']['lease']
        self.assertEqual(self.post('/jobs/'+jid+'/cancel').status_code,200)
        self.assertEqual(self.post('/worker/'+jid+'/start',{'lease':lease},True).status_code,409)
        self.assertEqual(self.client.get('/api/voice/jobs/'+jid).json()['state'],'cancelled')
        with sqlite3.connect(self.cfg['AUTH_DB_PATH']) as c:
            c.execute('UPDATE web_sessions SET expires=?',(time.time()-1,))
        self.assertEqual(self.client.get('/api/session').status_code,401)
        self.assertEqual(self.submit('after-session-expired').status_code,401)


    def test_atomic_competing_claims_and_preload_guard(self):
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        self.login()
        jid=self.submit().json()['id']
        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed=list(pool.map(lambda _:self.post('/worker/claim',worker=True).json()['job'],range(2)))
        self.assertEqual(sum(job is not None for job in claimed),1)
        self.assertEqual(next(job['id'] for job in claimed if job),jid)
        with patch('api.voice.os.getpid',return_value=-1):
            self.assertEqual(self.client.get('/api/voice/status').status_code,503)
        with self.assertLogs('api.voice',level='ERROR'):
            disabled=TestClient(load_voice_app({**self.cfg,'VOICE_WORKER_SECRET':'short'},auth=self.auth))
        self.assertEqual(disabled.get('/status').status_code,404)
        disabled.close()

    def test_cookie_replay_after_logout_and_password_source(self):
        self.login()
        token = self.client.cookies[COOKIE]
        self.assertEqual(self.client.post('/api/logout', headers=self.headers).status_code, 200)
        self.client.cookies.set(COOKIE, token)
        self.assertEqual(self.client.get('/api/session').status_code, 401)
        self.assertEqual(self.submit().status_code, 401)
        self.assertEqual(self.client.post('/api/login', json={'username':'admin','password':'littleredfloweradmin'}, headers=self.headers).status_code,401)
        self.login()

    def test_running_cancel_and_bad_lease_cannot_revive(self):
        self.login()
        jid=self.submit().json()['id']
        lease=self.start(jid)
        self.assertEqual(self.post('/worker/'+jid+'/start', {'lease':{}}, True).status_code,400)
        self.assertEqual(self.post('/jobs/'+jid+'/cancel').status_code,200)
        self.assertEqual(self.post('/worker/'+jid+'/result',{'lease':lease,'reply':'too late','state':'done'},True).status_code,409)
        self.assertEqual(self.client.get('/api/voice/jobs/'+jid).json()['state'],'cancelled')
        self.assertIsNone(self.post('/worker/claim',worker=True).json()['job'])

    def test_payload_limits_rate_and_worker_identity_separation(self):
        self.login()
        self.assertEqual(self.submit(text='x'*4001).status_code,400)
        self.assertEqual(self.client.post('/api/voice/jobs',content='x'*25000,headers={**self.headers,'Content-Type':'application/json'}).status_code,413)
        self.assertEqual(self.client.get('/api/voice/status',headers={'Origin':'https://evil.example'}).status_code,403)
        machine=TestClient(self.app,base_url='https://voice.example')
        self.assertEqual(machine.get('/api/voice/status',headers=self.worker).status_code,401)
        machine.close()
        for i in range(12):
            jid=self.submit('rate-key-for-job-'+str(i)).json()['id']
            self.assertEqual(self.post('/jobs/'+jid+'/cancel').status_code,200)
        self.assertEqual(self.submit('rate-over-limit-job').status_code,429)

    def test_persist_restart_and_expired_result(self):
        self.login()
        jid=self.submit().json()['id']
        lease=self.start(jid)
        self.voice.state.voice_lock.close()
        self.voice=create_voice_app(self.cfg,auth=self.auth)
        self.app=FastAPI();self.app.include_router(self.auth.router);self.app.mount('/api/voice',self.voice)
        cookies=dict(self.client.cookies)
        self.client.close();self.client=TestClient(self.app,base_url='https://voice.example',cookies=cookies)
        self.assertEqual(self.client.get('/api/voice/jobs/'+jid).json()['state'],'running')
        self.assertIsNone(self.post('/worker/claim',worker=True).json()['job'])
        with sqlite3.connect(self.path) as c:c.execute('UPDATE jobs SET expires=?',(time.time()-1,))
        self.assertEqual(self.post('/worker/'+jid+'/result',{'lease':lease,'reply':'late','state':'done'},True).status_code,409)

if __name__=='__main__':unittest.main()
