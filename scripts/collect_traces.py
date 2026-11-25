"""Capture real slow/error traces and correlated JSON log lines."""
import asyncio
import json
from pathlib import Path
import subprocess
import time
import httpx
root=Path(__file__).resolve().parents[1]
reports=root/'reports'
async def collect():
    found={}
    async with httpx.AsyncClient(timeout=15) as c:
        async def one():
            t=time.perf_counter()
            r=await c.post('http://localhost:8080/ask',json={'question':'Graceful shutdown xử lý SIGTERM thế nào?'},headers={'X-API-Key':'day14-lab-key'})
            elapsed=(time.perf_counter()-t)*1000
            kind='error' if r.status_code==503 else 'slow' if elapsed>1000 and r.status_code==200 else None
            if kind and kind not in found:
                found[kind]={'trace_id':r.headers.get('x-trace-id'), 'status':r.status_code,'client_ms':round(elapsed,2)}
        for _ in range(30):
            await asyncio.gather(*(one() for _ in range(10)))
            if len(found)==2: break
    return found
found=asyncio.run(collect())
time.sleep(7)
with httpx.Client() as c:
 for kind, data in found.items():
    trace=c.get('http://localhost:16686/api/v3/traces/'+data['trace_id']).json()
    (reports/f'trace-{kind}.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding='utf-8')
    spans=[s for rs in trace['result']['resourceSpans'] for ss in rs['scopeSpans'] for s in ss['spans']]
    for s in spans:s['duration_ms']=(int(s['endTimeUnixNano'])-int(s['startTimeUnixNano']))/1e6
    data['spans']=[{'name':s['name'],'ms':s['duration_ms'],'events':s.get('events',[])} for s in spans]
    data['total_ms']=(max(int(s['endTimeUnixNano']) for s in spans)-min(int(s['startTimeUnixNano']) for s in spans))/1e6
logs=subprocess.run(['docker','compose','-p','k5-day14-observability','logs','--no-log-prefix','agent'],cwd=root/'06-lab-complete/benchmark-observability/production',capture_output=True,text=True).stdout
for data in found.values():
    data['logs']=[line for line in logs.splitlines() if data['trace_id'] in line]
(reports/'observable-agent.log').write_text('\n'.join(line for item in found.values() for line in item['logs'])+'\n',encoding='utf-8')
(reports/'trace-evidence.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(found,ensure_ascii=False,indent=2))
