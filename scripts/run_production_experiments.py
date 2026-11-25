"""Collect scaling and chaos evidence against the real compose stack."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/'06-lab-complete/benchmark-observability/production'
REPORTS=ROOT/'reports'
BASE=['docker','compose','-p','k5-day14-observability']
STATE=REPORTS/'experiment-progress.json'

def status(phase):
    STATE.write_text(json.dumps({'phase':phase,'updated':datetime.now(timezone.utc).isoformat()}))
    print(phase,flush=True)

def docker(args, env=None, logfile='production-experiments.txt'):
    with (REPORTS/logfile).open('a') as log:
        return subprocess.run(BASE+args,cwd=LAB,env={**os.environ,**(env or {})},stdout=log,stderr=log).returncode

def snapshot():
    return httpx.get('http://localhost:9090/api/v1/alerts',timeout=10).json()['data']['alerts']

async def load(seconds):
    end=time.monotonic()+seconds
    counts={}
    async with httpx.AsyncClient(timeout=15) as client:
        async def worker():
            while time.monotonic()<end:
                try:
                    r=await client.post('http://localhost:8080/ask',json={'question':'Docker container là gì?'},headers={'X-API-Key':'day14-lab-key'})
                    code=str(r.status_code)
                except Exception:code='connection_error'
                counts[code]=counts.get(code,0)+1
        await asyncio.gather(*(worker() for _ in range(30)))
    return counts

async def observe(seconds):
    task=asyncio.create_task(load(seconds))
    start=time.monotonic()
    observations=[]
    while not task.done():
        await asyncio.sleep(5)
        observations.append({'elapsed_s':round(time.monotonic()-start,2),'alerts':snapshot()})
        (REPORTS/'chaos-live.json').write_text(json.dumps(observations,indent=2))
    return {'status_codes':await task,'observations':observations}

if __name__=='__main__':
    evidence={}
    for scale in (1,3):
        status(f'scale_{scale}: 100 users, 120 seconds')
        docker(['up','-d','--no-build','--scale',f'agent={scale}'])
        time.sleep(12)
        containers=subprocess.check_output(BASE+['ps','-q','agent'],cwd=LAB,text=True).split()
        evidence[f'scale_{scale}']={'containers':containers,'instances':len(containers)}
        (REPORTS/'experiment-evidence.json').write_text(json.dumps(evidence,indent=2))
        docker(['run','--rm','--no-deps','locust','-f','/mnt/locust/locustfile.py','--host','http://nginx','--headless','-u','100','-r','10','-t','2m','--csv',f'/mnt/results/scale_{scale}'],logfile=f'locust-scale-{scale}.txt')
    phases=[('AB_errors_and_latency',{'MOCK_ERROR_RATE':'0.2','MOCK_SLOW_RATE':'0.3'},165),
            ('C_large_model',{'LLM_MODEL':'mock-llm-large','MOCK_ERROR_RATE':'0.01','MOCK_SLOW_RATE':'0.03'},165)]
    for name,env,seconds in phases:
        status(name)
        docker(['up','-d','--no-build','--scale','agent=1','agent'],env=env)
        started=datetime.now(timezone.utc).isoformat()
        evidence[name]={'started_at':started,'env':env,**asyncio.run(observe(seconds))}
        (REPORTS/'experiment-evidence.json').write_text(json.dumps(evidence,indent=2))
        if name.startswith('AB'):
            (REPORTS/'alerts-two-firing.json').write_text(json.dumps(snapshot(),indent=2))
            status('AB_screenshot_ready')
            time.sleep(25)
    status('D_pause_instance')
    docker(['up','-d','--no-build','--scale','agent=3','agent'])
    time.sleep(15)
    instance=subprocess.check_output(BASE+['ps','-q','agent'],cwd=LAB,text=True).split()[0]
    subprocess.run(['docker','pause',instance],check=True)
    try:evidence['D_pause']={'container':instance,**asyncio.run(observe(60))}
    finally:subprocess.run(['docker','unpause',instance],check=True)
    status('E_v1_quality')
    docker(['up','-d','--no-build','--scale','agent=1','agent'],env={'AGENT_VERSION':'v1','MOCK_ERROR_RATE':'0'})
    time.sleep(12)
    with (REPORTS/'eval-production-v1.txt').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'06-lab-complete/benchmark-observability/develop/eval/run_eval.py'),'--url','http://localhost:8080','--api-key','day14-lab-key','--min-accuracy','1','--out',str(REPORTS/'eval-production-v1.json')],stdout=log,stderr=log)
    evidence['E_v1']={'alerts_at_end':snapshot()}
    (REPORTS/'experiment-evidence.json').write_text(json.dumps(evidence,indent=2))
    docker(['up','-d','--no-build','--scale','agent=1','agent'])
    status('complete')
