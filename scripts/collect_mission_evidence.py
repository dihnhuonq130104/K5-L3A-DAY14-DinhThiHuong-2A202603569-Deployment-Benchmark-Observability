"""Collect real HTTP evidence for Parts 1 and 4 without logging secrets."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import httpx

root = Path(__file__).resolve().parents[1]
report = root/'reports/mission-http.txt'

def run_app(folder, port, env=None):
    log = open(os.devnull, 'w')
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--port', str(port)],
        cwd=root/folder, env={**os.environ, **(env or {})}, stdout=log, stderr=log)
    for _ in range(80):
        try:
            httpx.get(f'http://127.0.0.1:{port}/openapi.json').raise_for_status()
            return process, log
        except Exception:
            time.sleep(0.1)
    raise RuntimeError('App failed to start')

with report.open('w', encoding='utf-8') as out:
    proc, log = run_app('01-localhost-vs-production/develop', 8011)
    try:
        r=httpx.post('http://127.0.0.1:8011/ask',params={'question':'Hello'})
        out.write('Part 1 query /ask: '+str(r.status_code)+' '+r.text+'\n')
    finally:
        proc.terminate(); proc.wait(); log.close()
    proc, log = run_app('04-api-gateway/production', 8014, {'JWT_SECRET':secrets.token_urlsafe(32)})
    try:
        with httpx.Client(base_url='http://127.0.0.1:8014') as client:
            r=client.post('/ask',json={'question':'Hello'})
            out.write('Part 4 no auth: '+str(r.status_code)+' '+r.text+'\n')
            r=client.post('/auth/token',json={'username':'student','password':'demo123'})
            out.write('POST /auth/token: '+str(r.status_code)+' [token redacted]\n')
            token=r.json()['access_token']
            codes=[]
            for _ in range(12):
                r=client.post('/ask',json={'question':'Docker'},headers={'Authorization':'Bearer '+token})
                codes.append(r.status_code)
                if len(codes)==1 or r.status_code==429:
                    out.write('POST /ask: '+str(r.status_code)+' '+r.text+'\n')
            out.write('12 sequential requests: '+str(codes)+'\n')
    finally:
        proc.terminate(); proc.wait(); log.close()
