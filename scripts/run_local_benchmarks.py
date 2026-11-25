"""Run reproducible local benchmarks, preserving the original KB baseline."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / '06-lab-complete/benchmark-observability/develop'
REPORTS = ROOT / 'reports'
PYTHON = sys.executable

def command(args, log):
    with (REPORTS / log).open('w') as output:
        result = subprocess.run([PYTHON, *args], cwd=LAB, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode not in (0, 1):
        raise RuntimeError(f'{args}: exit {result.returncode}')

def start(version, port, slow='0.03', errors='0.01'):
    env = {**os.environ, 'AGENT_VERSION': version, 'PORT': str(port),
           'MOCK_SLOW_RATE': slow, 'MOCK_ERROR_RATE': errors}
    log = (REPORTS / f'agent_{version}_{port}.log').open('w')
    proc = subprocess.Popen([PYTHON, 'app.py'], cwd=LAB, env=env, stdout=log, stderr=log)
    for _ in range(100):
        try:
            urllib.request.urlopen(f'http://localhost:{port}/health', timeout=1)
            return proc, log
        except Exception:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
    raise RuntimeError('Agent did not start')

def stop(proc, log):
    proc.terminate()
    proc.wait(timeout=15)
    log.close()

def evaluate(version, port, name, baseline=None):
    proc, log = start(version, port, errors='0')
    try:
        args = ['eval/run_eval.py', '--url', f'http://localhost:{port}',
                '--out', str(REPORTS / name), '--min-accuracy', '1.0']
        if baseline:
            args += ['--baseline', str(REPORTS / baseline)]
        command(args, name + '.txt')
    finally:
        stop(proc, log)

if __name__ == '__main__':
    REPORTS.mkdir(exist_ok=True)
    if '--fixed' in sys.argv:
        evaluate('v2', 8002, 'eval_v2_fixed.json', 'eval_v2.json')
        raise SystemExit(0)
    evaluate('v1', 8001, 'eval_v1.json')
    evaluate('v2', 8002, 'eval_v2.json')
    proc, log = start('v2', 8002)
    try:
        for concurrency in (1, 10, 50, 100):
            name = f'load_v2_c{concurrency}.json'
            command(['load_test.py', '--url', 'http://localhost:8002', '--requests', '300',
                     '--concurrency', str(concurrency), '--out', str(REPORTS/name)], name+'.txt')
    finally:
        stop(proc, log)
    for slow in ('0', '0.03', '0.1'):
        proc, log = start('v2', 8002, slow=slow)
        try:
            name = f'load_v2_slow_{slow}.json'
            command(['load_test.py', '--url', 'http://localhost:8002', '--requests', '300',
                     '--concurrency', '20', '--out', str(REPORTS/name)], name+'.txt')
        finally:
            stop(proc, log)
