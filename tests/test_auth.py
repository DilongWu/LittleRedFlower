"""Website login regression checks, independent of finance and voice setup."""
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import COOKIE, WebAuth


class WebAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def client(self, origin=None, local=False):
        cfg = {'AUTH_DB_PATH': self.temp.name+'/auth.db'}
        if origin:
            cfg['AUTH_PUBLIC_ORIGIN'] = origin
        if local:
            cfg['VOICE_LOCAL_TEST'] = '1'
        app = FastAPI()
        app.include_router(WebAuth(cfg).router)
        client = TestClient(app, base_url='http://site.example')
        self.addCleanup(client.close)
        return client

    def login(self, client, origin='https://site.example', **headers):
        return client.post('/api/login', json={
            'username': 'admin', 'password': 'littleredfloweradmin'
        }, headers={'Origin': origin, **headers})

    def test_https_origin_on_http_backend_login_session_logout(self):
        client = self.client()
        response = self.login(client)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Secure', response.headers['set-cookie'])
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        # The browser uses HTTPS; the test backend URL deliberately uses HTTP.
        client.cookies.set(COOKIE, response.cookies[COOKIE])
        self.assertEqual(client.get('/api/session').json(), {'username': 'admin'})
        self.assertEqual(client.post('/api/logout', headers={
            'Origin': 'https://site.example'
        }).status_code, 200)
        self.assertEqual(client.get('/api/session').status_code, 401)

    def test_cross_origin_missing_origin_and_http_origin_rejected(self):
        client = self.client()
        for origin in ('https://evil.example', 'http://site.example', 'null',
                       'https://site.example.evil', 'https://site.example:444',
                       'https://site.example/path'):
            with self.subTest(origin=origin):
                self.assertEqual(self.login(client, origin).status_code, 403)
                self.assertEqual(client.post('/api/logout', headers={
                    'Origin': origin
                }).status_code, 403)
        self.assertEqual(client.post('/api/login', json={}).status_code, 403)
        self.assertEqual(client.post('/api/logout').status_code, 403)

    def test_forwarded_headers_cannot_authorize_another_origin(self):
        client = self.client()
        self.assertEqual(self.login(client, 'https://evil.example', **{
            'X-Forwarded-Host': 'evil.example',
            'X-Forwarded-Proto': 'https',
            'Forwarded': 'host=evil.example;proto=https',
        }).status_code, 403)
        self.assertEqual(self.login(client, **{
            'X-Forwarded-Host': 'evil.example', 'X-Forwarded-Proto': 'http'
        }).status_code, 200)

    def test_configured_origin_and_host_remain_strict(self):
        client = self.client(origin='https://configured.example')
        self.assertEqual(self.login(client).status_code, 403)
        self.assertEqual(self.login(client, 'https://configured.example').status_code, 403)
        self.assertEqual(self.login(client, 'https://configured.example',
                                    Host='configured.example').status_code, 200)
        self.assertEqual(self.login(client, Host='evil.example').status_code, 403)

    def test_bad_password_still_returns_401(self):
        client = self.client()
        response = client.post('/api/login', json={
            'username': 'admin', 'password': 'wrong'
        }, headers={'Origin': 'https://site.example'})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('set-cookie', response.headers)

    def test_explicit_local_test_retains_http(self):
        client = self.client(local=True)
        self.assertEqual(self.login(client, 'http://site.example').status_code, 200)


if __name__ == '__main__':
    unittest.main()
