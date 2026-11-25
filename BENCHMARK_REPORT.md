# Benchmark & Observability Report — Day 14

**Họ tên:** Đinh Thị Hương
**Ngày chạy:** 25/11/2026 (Asia/Saigon)
**Môi trường:** Windows, Ubuntu 22.04 WSL2, Python 3.11.0rc1 (posix), Docker Desktop 29.6.2 Linux engine, 4 CPU / 8.33 GB RAM cấp cho Docker. Chi tiết: reports/environment.json.

## 1. SLO

| SLI | SLO | Lý do |
|---|---|---|
| p95 /ask | ≤ 500 ms | Phản hồi tương tác; đúng ngưỡng load_test.py |
| Error rate /ask | ≤ 2% | Giới hạn lỗi ứng dụng/upstream |
| Accuracy | 100% (23/23), không regression | Quality gate cho bộ golden nhỏ của lab |

SLO local khác ngưỡng cảnh báo production có sẵn (p95 > 1 giây, lỗi > 5%). Accuracy 100% trên 23 câu không chứng minh đúng với mọi câu ngoài bộ eval.

## 2. Benchmark hiệu năng

Mỗi lượt 300 request, v2, mock-llm-small. Các lượt concurrency chạy trước khi sửa KB; không thay đổi độ trễ và xác suất lỗi mặc định.

### 2.1 Concurrency

| Concurrency | RPS | p50 ms | p95 ms | p99 ms | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.58 | 189.8 | 220.0 | 1677.8 | 1.00% | PASS |
| 10 | 41.15 | 192.8 | 220.0 | 1686.6 | 2.33% | FAIL |
| 50 | 99.86 | 218.7 | 292.3 | 1722.4 | 1.00% | PASS |
| 100 | 58.21 | 390.8 | 3228.6 | 3517.6 | 2.33% | FAIL |

RPS tăng khi có nhiều request chờ I/O đồng thời. Mức tăng không hoàn toàn tuyến tính vì HTTP overhead, event loop, connection pool, CPU và đuôi latency. Đây là closed-loop benchmark trên cùng máy, chưa đo giới hạn của một hệ thống cloud độc lập. Trong phiên chạy local còn có tác vụ Docker/build dùng chung tài nguyên; các số này phản ánh môi trường lab, chưa phải phép đo cô lập.

### 2.2 Tail latency

Cùng 300 request, concurrency 20, chỉ thay MOCK_SLOW_RATE. MOCK_ERROR_RATE giữ 0.01; số liệu có biến thiên do mock ngẫu nhiên.

| MOCK_SLOW_RATE | avg ms | p95 ms | p99 ms |
|---|---|---|---|
| 0 | 194.5 | 223.2 | 237.8 |
| 0.03 | 248.4 | 228.0 | 1694.8 |
| 0.1 | 331.4 | 1692.5 | 1712.9 |

p99 nhạy với nhóm request chậm hiếm gặp; khi tỷ lệ chậm đạt 10%, p95 cũng nằm trong nhóm chậm. Average pha loãng các request chậm nên có thể trông tốt trong khi người dùng ở đuôi phân phối phải đợi lâu.

## 3. Benchmark chất lượng

Chạy v1, v2 baseline và v2 fixed với MOCK_ERROR_RATE=0 để tách lỗi tri thức khỏi lỗi upstream ngẫu nhiên. Giữ nguyên golden_dataset.jsonl. Baseline và fixed dùng cùng ngưỡng accuracy 100%.

| Chỉ số | v1 | v2 | v2 fixed |
|---|---|---|---|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100.00%) |
| Avg tokens/câu | 56.9 | 109.0 | 115.5 |
| Tổng cost USD | 0.000402 | 0.00076 | 0.000806 |
| Cost/câu đúng USD | 0.00040155 | 3.619e-05 | 3.505e-05 |
| p95 ms | 189.8 | 206.4 | 219.5 |
| Quality gate | FAIL | FAIL | PASS |

| ID sai ở v2 | Thiếu kiến thức | Sửa KB |
|---|---|---|
| security-02 | JWT so với API key | Bổ sung token, chữ ký, hết hạn và cách rotate/revoke |
| scaling-03 | Kubernetes HPA | Bổ sung CPU, memory và custom metrics |

Hai entry mới có keyword cụ thể, thêm trước entry chung. Chép cùng nội dung sang production. Không sửa thuật toán chấm hoặc dataset. Fixed đạt 23/23, danh sách regressions rỗng trong eval_v2_fixed.json.

Retrieval làm prompt dài hơn và có thêm bước tìm tài liệu nên token/cost/latency tăng. Cần đánh giá cost/câu đúng: chi phí rẻ của một câu sai không tạo cùng giá trị với câu đúng. Đây là giá mô phỏng, không phải hóa đơn nhà cung cấp.

### Quality gate trong CI

Khởi động agent v2 với MOCK_ERROR_RATE=0, chờ health rồi chạy:
```bash
python eval/run_eval.py --url http://localhost:8002 --min-accuracy 1.0 --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json
```
Không thêm `|| true` ở job CI: exit code 1 làm job fail nếu accuracy thiếu hoặc có regression. Đặt job thành required check trong branch protection để chặn merge. Script orchestration local cho phép baseline fail để lưu bằng chứng; khi dùng trong CI phải dùng exit code trực tiếp.

## 4. Observability stack

### 4.1 Bằng chứng

- [Grafana khi có tải](screenshots/grafana-dashboard.png), cổng 3001 để tránh ứng dụng đang chiếm 3000.
- [Trace chậm](screenshots/jaeger-slow-trace.png).
- [Trace lỗi với event exception](screenshots/jaeger-error-trace.png).
- [Prometheus Alerts](screenshots/prometheus-alert-firing.png).

Đã sửa Dockerfile mẫu: home user phải là /home/agent vì dependencies được copy vào /home/agent/.local. Giữ một Uvicorn worker/container để Prometheus metric không phân tán trong nhiều process.

### 4.2 Thí nghiệm chaos

A và B được chạy **kết hợp**: MOCK_ERROR_RATE=0.2, MOCK_SLOW_RATE=0.3; không coi đây là hai thí nghiệm độc lập. Sau đó chạy C, D, E theo thứ tự. Dùng 30 request đồng thời cho tải chaos; đây là tải khác với bài Locust scaling. Thời gian dưới đây đo từ khi compose up hoàn tất đến lần poll đầu thấy firing; poll mỗi khoảng 5 giây.

| Thí nghiệm | Alert quan sát firing | Lần đầu quan sát (giây) | Panel/giải thích |
|---|---|---|---|
| A+B: lỗi 20%, chậm 30% | LLMCostBurnRateHigh<br>AgentHighErrorRate<br>AgentHighLatencyP95 | 5.00<br>91.87<br>148.04 | Error rate và latency p95 tăng; hai alert có for=1m và 2m. |
| C: mock-llm-large | AgentHighErrorRate<br>AgentHighLatencyP95<br>LLMCostBurnRateHigh | 5.00<br>5.00<br>5.00 | Cost burn rate tăng; alert cost có thể đã firing trước C do tải trước đó. |
| D: pause một instance | LLMCostBurnRateHigh<br>AgentInstanceDown | 5.00<br>40.76 | Instance up giảm, Prometheus scrape timeout; Nginx có timeout/failover. |
| E: agent v1 | Không thiết kế alert correctness trong stack | Không suy ra thời gian phát hiện chất lượng | Eval production: 1/23, 0 lỗi HTTP; kết quả reports/eval-production-v1.json. Cần golden/canary eval riêng. |

File gốc: `reports/experiment-evidence.json`; snapshot A+B: `reports/alerts-two-firing.json`. Alert đã firing từ giai đoạn trước không chứng minh được thời gian phát hiện mới của C hoặc E. Tải chaos cao cũng có thể làm alert cost firing ngay với model nhỏ. Không diễn giải alert cost như hóa đơn thật: mock chỉ mô phỏng USD/token.

Counter dùng rate để xử lý reset. Histogram dùng histogram_quantile trên sum(rate(bucket)) theo le. Không dùng user_id hoặc request_id làm label vì cardinality tăng không giới hạn; đặt request_id/trace_id trong logs/traces.

### 4.3 Debug bằng trace

**Trace chậm:** `e54355d53c3caa9ffe34c9d8024f4c0a`, HTTP 200, tổng 1701.847 ms.
Span gọi LLM `chat mock-llm-small`: 1681.352 ms (98.80% tổng trace). Span agent.run bao toàn bộ logic nên không cộng duration các span lồng nhau.
```json
{"ts": "2026-11-25T09:19:03.208478+00:00", "level": "INFO", "service": "observable-agent", "instance": "7c256fb6e9a9", "event": "llm_call", "trace_id": "e54355d53c3caa9ffe34c9d8024f4c0a", "span_id": "cd0d19bac5e92fb6", "request_id": "42105cf98f96", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 75, "output_tokens": 39, "cost_usd": 3.5e-05, "llm_ms": 1682.3}
```

**Trace lỗi:** `66c9eecef096701d0ab751d0c5152443`, HTTP 503, tổng 111.765 ms.
Span gọi LLM `chat mock-llm-small`: 85.650 ms (76.63% tổng trace). Span agent.run bao toàn bộ logic nên không cộng duration các span lồng nhau.
```json
{"ts": "2026-11-25T09:19:03.328532+00:00", "level": "INFO", "service": "observable-agent", "instance": "7c256fb6e9a9", "event": "llm_error", "trace_id": "66c9eecef096701d0ab751d0c5152443", "span_id": "4cf78b10c8b6d5fb", "request_id": "d165f455fc7a", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

Bản raw OTLP từ Jaeger: `reports/trace-slow.json`, `reports/trace-error.json`; log trích theo đúng trace_id: `reports/observable-agent.log`. Trace lỗi có event exception với type utils.mock_llm.LLMError.

## 5. Benchmark scaling

Locust headless: 100 users, spawn 10/s, 2 phút, cùng mock configuration mặc định. Thêm `--no-deps` khi compose run để không reset replica theo deploy.replicas=2 của mẫu. Số container thực tế được lưu trong experiment-evidence.json: 1 và 3. Bảng lấy dòng POST /ask; file CSV còn có /health và Aggregated.

| Instance | RPS /ask | p50 ms | p95 ms | p99 ms | Failure / tổng |
|---|---|---|---|---|---|
| 1 | 61.68 | 190 | 240 | 1700 | 71 / 7121 |
| 3 | 61.57 | 190 | 250 | 1700 | 67 / 7070 |

RPS thay đổi từ 61.68 lên 61.57; p95 từ 240 lên 250 ms. Không tăng 3 lần: 100 user có thời gian nghỉ 0.5–2 giây, mock chủ yếu chờ I/O, cả load generator và containers dùng cùng máy. Scale không loại bỏ tail latency upstream. Một lần chạy mỗi mức chưa đủ kết luận định lượng chắc chắn về năng lực tối đa. Lượt scale_1 trước bị gián đoạn trong phiên làm việc, làm duration/RPS không phù hợp; đã lưu riêng reports/scale_1_interrupted_stats.csv và chạy lại 2 phút để lấy bảng này.

## 6. Điều rút ra

1. p95/p99 cho thấy request chậm bị average che khuất.
2. Cần quality gate riêng: HTTP 200 không chứng minh câu trả lời đúng.
3. Metrics khoanh vùng sự cố; trace tìm span chậm; log có trace_id giúp đối chiếu cùng request.

Khi chạy thật cần thêm token usage theo model, ngân sách còn lại, queue depth, provider timeout/rate-limit và alert theo error-budget burn rate. Cost guard Part 6 cần atomic reservation để tránh vượt ngân sách do request đồng thời.
