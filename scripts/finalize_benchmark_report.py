"""Assemble measured production evidence into the benchmark report."""
import csv
import json
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
r=root/'reports'
e=json.loads((r/'experiment-evidence.json').read_text(encoding='utf-8'))
t=json.loads((r/'trace-evidence.json').read_text(encoding='utf-8'))
p=root/'BENCHMARK_REPORT.md'
s=p.read_text(encoding='utf-8')
start=s.index('## 4. Observability stack')
end=s.index('## 6. Điều rút ra')
lines=['## 4. Observability stack','','### 4.1 Bằng chứng','','- [Grafana khi có tải](screenshots/grafana-dashboard.png), cổng 3001 để tránh ứng dụng đang chiếm 3000.','- [Trace chậm](screenshots/jaeger-slow-trace.png).','- [Trace lỗi với event exception](screenshots/jaeger-error-trace.png).','- [Prometheus Alerts](screenshots/prometheus-alert-firing.png).','', 'Đã sửa Dockerfile mẫu: home user phải là /home/agent vì dependencies được copy vào /home/agent/.local. Giữ một Uvicorn worker/container để Prometheus metric không phân tán trong nhiều process.','','### 4.2 Thí nghiệm chaos','','A và B được chạy **kết hợp**: MOCK_ERROR_RATE=0.2, MOCK_SLOW_RATE=0.3; không coi đây là hai thí nghiệm độc lập. Sau đó chạy C, D, E theo thứ tự. Dùng 30 request đồng thời cho tải chaos; đây là tải khác với bài Locust scaling. Thời gian dưới đây đo từ khi compose up hoàn tất đến lần poll đầu thấy firing; poll mỗi khoảng 5 giây.','', '| Thí nghiệm | Alert quan sát firing | Lần đầu quan sát (giây) | Panel/giải thích |','|---|---|---|---|']
for name,label,explain in [('AB_errors_and_latency','A+B: lỗi 20%, chậm 30%','Error rate và latency p95 tăng; hai alert có for=1m và 2m.'),('C_large_model','C: mock-llm-large','Cost burn rate tăng; alert cost có thể đã firing trước C do tải trước đó.'),('D_pause','D: pause một instance','Instance up giảm, Prometheus scrape timeout; Nginx có timeout/failover.')]:
 if name not in e:continue
 first={}
 for obs in e[name]['observations']:
  for alert in obs['alerts']:
   if alert['state']=='firing':first.setdefault(alert['labels']['alertname'],obs['elapsed_s'])
 lines.append('| '+label+' | '+('<br>'.join(first) or 'Không quan sát')+' | '+('<br>'.join(f'{v:.2f}' for v in first.values()) or '—')+' | '+explain+' |')
lines+=['| E: agent v1 | Không thiết kế alert correctness trong stack | Không suy ra thời gian phát hiện chất lượng | Eval production: 1/23, 0 lỗi HTTP; kết quả reports/eval-production-v1.json. Cần golden/canary eval riêng. |','','File gốc: `reports/experiment-evidence.json`; snapshot A+B: `reports/alerts-two-firing.json`. Alert đã firing từ giai đoạn trước không chứng minh được thời gian phát hiện mới của C hoặc E. Tải chaos cao cũng có thể làm alert cost firing ngay với model nhỏ. Không diễn giải alert cost như hóa đơn thật: mock chỉ mô phỏng USD/token.','','Counter dùng rate để xử lý reset. Histogram dùng histogram_quantile trên sum(rate(bucket)) theo le. Không dùng user_id hoặc request_id làm label vì cardinality tăng không giới hạn; đặt request_id/trace_id trong logs/traces.','','### 4.3 Debug bằng trace','']
for kind,title in [('slow','Trace chậm'),('error','Trace lỗi')]:
 data=t[kind]
 leaf=max((span for span in data['spans'] if span['name'].startswith('chat ')),key=lambda span:span['ms'])
 lines += [f"**{title}:** `{data['trace_id']}`, HTTP {data['status']}, tổng {data['total_ms']:.3f} ms.",f"Span gọi LLM `{leaf['name']}`: {leaf['ms']:.3f} ms ({leaf['ms']/data['total_ms']*100:.2f}% tổng trace). Span agent.run bao toàn bộ logic nên không cộng duration các span lồng nhau.", '```json',data['logs'][0] if data['logs'] else '{}','```','']
lines+=['Bản raw OTLP từ Jaeger: `reports/trace-slow.json`, `reports/trace-error.json`; log trích theo đúng trace_id: `reports/observable-agent.log`. Trace lỗi có event exception với type utils.mock_llm.LLMError.','','## 5. Benchmark scaling','','Locust headless: 100 users, spawn 10/s, 2 phút, cùng mock configuration mặc định. Thêm `--no-deps` khi compose run để không reset replica theo deploy.replicas=2 của mẫu. Số container thực tế được lưu trong experiment-evidence.json: 1 và 3. Bảng lấy dòng POST /ask; file CSV còn có /health và Aggregated.','','| Instance | RPS /ask | p50 ms | p95 ms | p99 ms | Failure / tổng |','|---|---|---|---|---|---|']
(root/'benchmark-results').mkdir(exist_ok=True)
rows=[]
for count in (1,3):
 source=root/f'06-lab-complete/benchmark-observability/production/benchmark-results/scale_{count}_stats.csv'
 shutil.copy2(source,root/'benchmark-results'/source.name)
 with source.open() as f:row=next(v for v in csv.DictReader(f) if v['Name']=='/ask')
 rows.append(row)
 lines.append(f"| {count} | {float(row['Requests/s']):.2f} | {row['50%']} | {row['95%']} | {row['99%']} | {row['Failure Count']} / {row['Request Count']} |")
lines+=['',f"RPS thay đổi từ {float(rows[0]['Requests/s']):.2f} lên {float(rows[1]['Requests/s']):.2f}; p95 từ {rows[0]['95%']} lên {rows[1]['95%']} ms. Không tăng 3 lần: 100 user có thời gian nghỉ 0.5–2 giây, mock chủ yếu chờ I/O, cả load generator và containers dùng cùng máy. Scale không loại bỏ tail latency upstream. Một lần chạy mỗi mức chưa đủ kết luận định lượng chắc chắn về năng lực tối đa. Lượt scale_1 trước bị gián đoạn trong phiên làm việc, làm duration/RPS không phù hợp; đã lưu riêng reports/scale_1_interrupted_stats.csv và chạy lại 2 phút để lấy bảng này.",'']
p.write_text(s[:start]+'\n'.join(lines)+'\n'+s[end:],encoding='utf-8')
