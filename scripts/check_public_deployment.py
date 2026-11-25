"""Check cloud contract without writing or printing the API key."""
import argparse
import getpass
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

parser=argparse.ArgumentParser()
parser.add_argument('--url',required=True)
parser.add_argument('--public-only',action='store_true')
args=parser.parse_args()
base=args.url.rstrip('/')
key='' if args.public_only else os.getenv('AGENT_API_KEY') or getpass.getpass('API key tu Render Environment (khong hien khi nhap): ')
cases=[('health','GET','/health',None,200,False),('ready','GET','/ready',None,200,False),('missing_key','POST','/ask',{'question':'Hello'},401,False)]
if not args.public_only:cases.append(('valid_key','POST','/ask',{'question':'Docker'},200,True))
results=[]
for name,method,path,body,expected,auth in cases:
 headers={'Content-Type':'application/json'}
 if auth:headers['X-API-Key']=key
 request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body else None,headers=headers,method=method)
 try:
  with urllib.request.urlopen(request,timeout=120) as response:
   status=response.status; text=response.read().decode()
 except urllib.error.HTTPError as error:
  status=error.code;text=error.read().decode()
 results.append({'case':name,'method':method,'path':path,'expected':expected,'status':status,'passed':status==expected,'body':text})
 print(name,status,'PASS' if status==expected else 'FAIL')
root=Path(__file__).resolve().parents[1]
(root/'reports/cloud-checks.json').write_text(json.dumps({'url':base,'checks':results},ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
