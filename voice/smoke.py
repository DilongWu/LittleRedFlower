"""Isolated HTTP relay + Node worker E2E; explicit mock agent, no Gateway calls."""
import os
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.voice import create_voice_app
from api.auth import WebAuth


def main():
    with tempfile.TemporaryDirectory() as folder:
        sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
        origin='http://127.0.0.1:'+str(sock.getsockname()[1])
        code=secrets.token_urlsafe(32);secret=secrets.token_urlsafe(32)
        app=FastAPI()
        cfg=dict(VOICE_ENABLED='1',VOICE_LOCAL_TEST='1',VOICE_PUBLIC_ORIGIN=origin,
            ADMIN_USERNAME='test-owner',ADMIN_PASSWORD=code,AUTH_DB_PATH=folder+'/auth.db',VOICE_WORKER_SECRET=secret,VOICE_DB_PATH=folder+'/voice.db',
            VOICE_SINGLE_INSTANCE='1',VOICE_INSTANCE_COUNT='1')
        auth=WebAuth(cfg)
        voice=create_voice_app(cfg,auth=auth)
        app.include_router(auth.router)
        app.mount('/api/voice',voice)
        app.mount('/voice',StaticFiles(directory='web/public/voice',html=True))
        app.mount('/',StaticFiles(directory='web/dist',html=True))
        server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:raise RuntimeError('test server startup failed')
                time.sleep(.01)
            result=subprocess.run(['node','voice/smoke.mjs'],env={**os.environ,'TEST_ORIGIN':origin,'TEST_CODE':code,'TEST_WORKER_SECRET':secret},timeout=300 if os.environ.get('TEST_REAL_AGENT') == '1' else 90)
            if result.returncode:raise SystemExit(result.returncode)
        finally:
            server.should_exit=True;thread.join(10);sock.close();voice.state.voice_lock.close()

if __name__=='__main__':main()
