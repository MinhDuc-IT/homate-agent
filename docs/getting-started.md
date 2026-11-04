# Cài đặt và vận hành HomeMate

Các lệnh dưới đây dùng PowerShell. Chạy từ thư mục `homate-agent` trừ khi có lệnh `cd` khác.

## Cấu hình môi trường

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`.env` chứa cấu hình riêng và được Git bỏ qua. Không ghi đè file nếu đã điền key. Biến môi trường của process ưu tiên hơn giá trị trong `.env`.

| Biến | Ý nghĩa |
|---|---|
| POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD | Database/user/password của container PostgreSQL |
| POSTGRES_PORT | Cổng PostgreSQL trên host; mặc định 55433 |
| DATABASE_URL | Kết nối PostgreSQL cho backend và Alembic local |
| APP_ENV | development, test hoặc production |
| JWT_SECRET | Secret ký token; cần thay giá trị phát triển khi triển khai |
| LLM_PROVIDER | openrouter hoặc openai |
| OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME | Key và model khi chọn OpenRouter |
| OPENAI_API_KEY, OPENAI_MODEL_NAME | Key và model khi chọn OpenAI |
| BACKEND_URL | Backend mà AI service local gọi; mặc định http://127.0.0.1:8000 |
| WEATHER_API_KEY | Tùy chọn, bật dữ liệu thời tiết từ OpenWeather |

Cấu hình OpenRouter:

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-private-key
OPENROUTER_MODEL_NAME=openai/gpt-4o-mini
```

Chỉ điền key chưa đủ: `LLM_PROVIDER` phải chọn đúng provider. Model phải khả dụng với tài khoản/provider và hỗ trợ Chat Completions function calling. Không đặt key trong biến `VITE_*`, vì cấu hình frontend có thể xuất hiện trong browser bundle.

Đổi sang OpenAI bằng `LLM_PROVIDER=openai`, cấu hình `OPENAI_API_KEY` và `OPENAI_MODEL_NAME`. Key của provider không được chọn sẽ không được dùng.

## Docker

Cần Docker Desktop với Linux containers. Dừng các server local chiếm cổng 5173, 8000 hoặc 8010 trước khi chạy cùng bộ dịch vụ bằng Docker.

```powershell
docker compose up --build -d
docker compose ps
```

| Service | Cổng host | Cổng container |
|---|---|---|
| web | 5173 | 80 |
| backend | 8000 | 8000 |
| ai-service | 8010 | 8010 |
| db | POSTGRES_PORT, mặc định 55433 | 5432 |

Backend Docker luôn dùng `db:5432`; `DATABASE_URL` trong `.env` dành cho local không thay địa chỉ nội bộ này. AI service Docker dùng `http://backend:8000`. Frontend Nginx proxy `/api/ai/` về AI service, `/api/` và `/ws/` về backend.

Backend chạy `alembic upgrade head`, khởi tạo dữ liệu mẫu nếu cần, rồi nhận request. Lần khởi động đầu có thể mất thời gian để tạo dữ liệu điện năng.

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8010/health
Invoke-RestMethod http://localhost:8010/api/ai/status
```

`configured=true` chỉ xác nhận provider đang chọn có key, không chứng minh key/model hợp lệ hoặc còn hạn mức. Có thể thử một câu tra cứu trong trang `/assistant` để kiểm tra LLM thật; thao tác này gọi provider.

### Áp dụng cấu hình và cập nhật code

Sau khi sửa provider/key:

```powershell
docker compose up -d --force-recreate ai-service
```

`docker compose restart` giữ environment của container, nên không đủ để áp dụng giá trị `.env` mới. Khi code thay đổi, build lại các service tương ứng hoặc cả bộ:

```powershell
docker compose up --build -d
```

### Logs và dừng ứng dụng

```powershell
docker compose logs --tail 100 backend ai-service
docker compose logs -f ai-service
docker compose down
```

`postgres_data` giữ dữ liệu qua `down`. Lệnh `docker compose down -v` xóa volume dữ liệu; chỉ dùng khi chủ động muốn khởi tạo lại database.

## Phát triển local

Cần Python 3.11+, Node.js 22.22+ và PostgreSQL 17+. Có thể chỉ chạy database bằng Docker:

```powershell
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./apps/backend[test]" -e "./apps/ai-service[test]"
```

Nếu dùng PostgreSQL đã cài trên máy, tạo database/user riêng, đặt `DATABASE_URL` tương ứng và bỏ lệnh chạy container db.

### Terminal 1: backend

```powershell
$env:DATABASE_URL = "postgresql+psycopg://homate:homate_local@127.0.0.1:55433/homate"
cd apps/backend
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m uvicorn homate.bootstrap:create_app --factory --reload --host 127.0.0.1 --port 8000
```

URL trên dùng thông tin mẫu; thay bằng credentials và port của bạn. Backend đọc `.env` ở gốc project; Alembic yêu cầu `DATABASE_URL` trong môi trường process.

### Terminal 2: AI service

Từ gốc project:

```powershell
.\.venv\Scripts\python.exe -m uvicorn homate_ai.bootstrap:create_app --factory --reload --host 127.0.0.1 --port 8010
```

AI service đọc provider/key/model từ `.env`. Sau khi sửa `.env`, khởi động lại process; không dựa vào auto reload để nhận thay đổi file môi trường.

### Terminal 3: frontend

```powershell
cd apps/web
npm.cmd ci
npm.cmd run dev
```

Vite proxy `/api/ai` về cổng 8010, `/api` và `/ws` về cổng 8000. Không cần API key trong frontend.

## Đăng nhập và sử dụng

Mở http://localhost:5173, chọn Minh Đức và nhập PIN 1234. Các tài khoản mẫu chỉ dành cho phát triển; thay PIN và secret khi triển khai.

Trang `/assistant` có thể nhận:

- “Thiết bị nào đang bật?”
- “Điện năng đèn phòng khách trong 7 ngày tính đến ngày 2026-10-01.”
- “Tạo kịch bản đi ngủ để tắt đèn phòng khách.”
- “Liệt kê các lịch phòng khách.”
- “Tắt lịch bật đèn buổi sáng.”

Agent tra cứu dữ liệu bằng tools; nếu có thao tác thay đổi dữ liệu, kiểm tra nội dung và bấm Xác nhận hoặc Từ chối trước thời hạn. Quản lý kịch bản/lịch cần admin. Các loại câu mơ hồ, chuỗi nhiều thao tác và memory được mô tả trong [kiến trúc AI](ai-architecture.md).

## Kiểm thử

Backend integration tests dùng PostgreSQL thật. User test cần CREATEDB; test software tạo database có tên ngẫu nhiên rồi chỉ xóa database đó. Test catalog dùng schema riêng. Không có TEST_DATABASE_URL thì integration tests được skip.

```powershell
cd apps/backend
$env:TEST_DATABASE_URL = "postgresql+psycopg://homate:homate_local@127.0.0.1:55433/homate"
..\..\.venv\Scripts\python.exe -m pytest -q
cd ../ai-service
..\..\.venv\Scripts\python.exe -m pytest -q
cd ../web
npm.cmd run build
npx.cmd playwright test
```

Playwright cần backend cổng 8000 và Microsoft Edge. Cấu hình tự khởi động Vite nếu chưa chạy; phản hồi chat được giả lập, proposal/decision gọi backend thật. Các test AI dùng model/HTTP transport giả lập và không sử dụng key trong `.env` để gọi LLM thật.

## Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Docker không kết nối daemon | Mở Docker Desktop, chờ Linux engine sẵn sàng |
| Không bind được port | Kiểm tra ứng dụng đang dùng port; đổi POSTGRES_PORT cho db rồi chạy compose up -d để tạo lại container |
| Chat báo thiếu API key | Kiểm tra LLM_PROVIDER và key của đúng provider, sau đó recreate AI container |
| Chat báo LLM không phản hồi hợp lệ | Kiểm tra model hỗ trợ tools, key, hạn mức và kết nối provider |
| Key đã sửa nhưng vẫn lỗi cũ | Recreate container thay vì chỉ restart; local thì khởi động lại process |
| Backend chưa sẵn sàng | Xem migration/startup logs, kết nối PostgreSQL và đợi seed hoàn tất |
| Xác nhận hết hạn hoặc đối tượng đã thay đổi | Tra cứu trạng thái hiện tại rồi gửi yêu cầu mới |
| Receipt còn executing sau khi process dừng | Kiểm tra trạng thái thực tế trước khi tạo lại thao tác; không tự chạy lại receipt |
