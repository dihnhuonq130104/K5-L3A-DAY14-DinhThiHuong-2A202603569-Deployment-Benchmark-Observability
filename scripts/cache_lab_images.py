"""Populate official image tags through BuildKit when daemon pulls fail."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
images=['grafana/grafana:13.2.4','prom/prometheus:v3.16.0','jaegertracing/jaeger:2.23.0','locustio/locust:2.47.0']
def build(image):
    with open('reports/image-'+image.replace('/','-').replace(':','-')+'.txt','w') as log:
        result=subprocess.run(['docker','build','-t',image,'-'],input='FROM '+image+'\n',text=True,stdout=log,stderr=log)
    print(image,result.returncode,flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(build,images))
