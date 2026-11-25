# Deployment — Day 14

## Public URL
https://day14-agent-tb33.onrender.com

## Platform
Render — Blueprint labday14; agent và Redis dùng plan Free, region Singapore.

## Trạng thái đã xác minh
- GET /health → **200**, body `{"status":"ok"}`.
- GET /ready → **200**, body `{"status":"ready"}`: Redis cloud kết nối được.
- POST /ask thiếu API key → **401**.
- POST /ask có API key → **200**, trả câu trả lời về Docker và cost_usd.

**PASS 4/4 kiểm tra cloud.** Người học nhập key vào hộp thoại che ký tự; key không được ghi vào report hoặc Git.

Bằng chứng HTTP thực tế: `reports/cloud-checks.json`. Ảnh `screenshots/dashboard.png` do người học cung cấp cho thấy Blueprint sync commit 184f547 thành công, tạo đủ day14-redis và day14-agent. Ảnh `screenshots/running.png` chụp endpoint health public.

## Cấu hình có sẵn
Source: `06-lab-complete/`. Có `railway.toml`, `render.yaml` và Dockerfile production.

### Railway
1. Tạo project, thêm Redis và service từ repo GitHub này.
2. Đặt Root Directory của agent là `06-lab-complete`.
3. Đặt REDIS_URL tham chiếu Redis; tạo AGENT_API_KEY ngẫu nhiên bằng biến môi trường private.
4. Đặt ENVIRONMENT=production, RATE_LIMIT_PER_MINUTE=10, DAILY_BUDGET_USD=1, MONTHLY_BUDGET_USD=10.
5. Deploy, generate domain rồi chạy 4 lệnh bên dưới.

### Render
1. Đăng nhập Render bằng GitHub và chọn repo bài làm.
2. Tạo Blueprint từ `render.yaml` ở gốc repo (bản sao cấu hình trong `06-lab-complete/render.yaml`); web service có root directory `06-lab-complete`. Cả hai service khai báo plan free, region singapore.
3. Blueprint tạo agent và Redis keyvalue, generate API key và tham chiếu connectionString.
4. Nếu tài khoản/gói miễn phí không hỗ trợ kết nối Redis cần thiết, hỏi Lab Coach trước khi chọn gói tính phí.
5. Deploy rồi kiểm tra `/ready` trả 200.

## Biến môi trường
PORT do nền tảng cấp; ENVIRONMENT, AGENT_API_KEY, REDIS_URL, RATE_LIMIT_PER_MINUTE, DAILY_BUDGET_USD, MONTHLY_BUDGET_USD. Không chép giá trị secret vào file này.

## Tự kiểm tra trên cloud
Đặt BASE là URL HTTPS thật, AGENT_API_KEY trong shell riêng rồi chạy:
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```
Kỳ vọng lần lượt 200, 200, 401, 200. Lưu output thật vào reports và chụp dashboard, service running, test results vào screenshots. Che secret trước khi chụp.

## Bằng chứng đã lưu
- `reports/cloud-checks.json`: bốn response HTTP thật, không chứa key.
- `screenshots/dashboard.png`: Blueprint tạo Redis và agent thành công.
- `screenshots/running.png`: endpoint health public trả status ok.
- `screenshots/test.png`: ảnh trang hiển thị bốn kết quả từ cloud-checks.json.


## Kiểm tra có key mà không lộ secret
Sau khi có URL và service live, chạy tại gốc repo:
```powershell
python scripts/check_public_deployment.py --url https://day14-agent-tb33.onrender.com
```
Script hỏi API key qua getpass (không echo, không ghi key vào báo cáo). Lấy giá trị AGENT_API_KEY ở Render → day14-agent → Environment và dán vào prompt; không gửi key trong chat. Kết quả 4 trường hợp lưu trong reports/cloud-checks.json.

Nếu Terminal không dán được key, thêm `--gui-key` vào lệnh để nhập trong hộp thoại có che ký tự.
