# HomeMate

Làm lại phần software của P-072 với giao diện gốc React, FastAPI và PostgreSQL. AI sẽ được tích hợp sau; phần software hoạt động độc lập.

## Chức năng

- Đăng nhập PIN, refresh cookie và phân quyền admin/thành viên.
- Dashboard, phòng, thiết bị, điều khiển thủ công và WebSocket có xác thực.
- Quản lý thành viên; kịch bản và các bước điều khiển, thực thi và kiểm tra xung đột.
- Lịch một lần/lặp lại, bật/tắt lịch, worker thực thi và lịch sử chạy.
- Báo cáo điện năng, lấy mẫu/tổng hợp dữ liệu; cài đặt, nhật ký, chính sách xác nhận và giả lập phòng.
- Gợi ý phòng trống bằng quy tắc; thao tác nhạy cảm xác nhận thủ công.

Giữ bố cục và tài nguyên giao diện của P-072. Camera dùng dữ liệu minh họa; Unity WebGL và kết nối phần cứng chưa triển khai. Điện năng được ước tính theo trạng thái/công suất thiết bị mô phỏng. Không chạy LLM/STT/TTS; trang AI hiển thị chờ tích hợp.

Seed giống P-072: Michelin Bois, 6 phòng, 22 thiết bị, 4 thành viên. Đăng nhập **Minh Đức / PIN 1234**. Chưa nhập dữ liệu SQLite cá nhân từ project cũ; P-072 không bị sửa.

## Docker

```powershell
cd homate-agent
Copy-Item .env.example .env
docker compose up --build -d
```

Giao diện http://localhost:5173; Swagger http://localhost:8000/docs. Backend tự chạy migration. Volume postgres_data giữ dữ liệu qua docker compose down. Đổi PIN mẫu và JWT_SECRET trước khi triển khai.

## Local

Python 3.11+, Node.js 22.22+, PostgreSQL 17+. Từ homate-agent, tạo database/user riêng và đặt DATABASE_URL tương ứng:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./apps/backend[test]"
$env:DATABASE_URL = "postgresql+psycopg://homate:homate_local@127.0.0.1:55433/homate"
cd apps/backend
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m uvicorn homate.bootstrap:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Terminal khác:

```powershell
cd homate-agent/apps/web
npm.cmd ci
npm.cmd run dev
```

Vite proxy /api và /ws về backend; Docker dùng Nginx. Backend đọc .env gốc project và biến môi trường; Alembic dùng DATABASE_URL trong môi trường. Cấu hình mẫu ở .env.example.

## Clean Architecture

```text
apps/backend/src/homate/
  bootstrap.py, software_bootstrap.py  # Composition root
  application/household.py             # Use cases + repository port
  modules/
    home/domain/, home/application/   # Thiết bị, trạng thái phòng
    identity/domain/                  # PIN
    automation/domain/, application/  # Quy tắc lịch và service
    energy/application/               # Port báo cáo điện năng
    catalog/                          # Scaffold cũ, không mount vào app hiện tại
  presentation/                       # HTTP/auth/WebSocket routes
  infrastructure/
    postgres/                         # Persistence adapters
    tokens.py, realtime.py, weather.py
  worker.py                           # Scheduler, energy, occupancy
apps/backend/migrations/              # Alembic
apps/web/src/
  screens/, components/               # Giao diện gốc P-072
  context/, hooks/, services/          # State và HTTP adapters
  config/features.ts                  # AI mặc định tắt
```

Domain/application không phụ thuộc FastAPI/PostgreSQL. Presentation gọi use cases; infrastructure hiện thực port; composition root nối các thành phần. Frontend giữ cấu trúc màn hình gốc để bảo toàn giao diện, chưa tách toàn bộ thành feature modules.

PostgreSQL namespace homate dùng JSONB, TIMESTAMPTZ, khóa ngoại và transaction. Migration 0001 giữ scaffold ban đầu; 0002 tạo phần software. Seed có khóa chống khởi tạo đồng thời. Scheduler hiện dành cho một backend process; lịch sử có unique key tránh chạy lặp cùng mốc.

## Kiểm thử

```powershell
cd homate-agent/apps/backend
$env:TEST_DATABASE_URL = "postgresql+psycopg://homate:homate_local@127.0.0.1:55433/homate"
..\..\.venv\Scripts\python.exe -m pytest -q
```

Test software tạo database ngẫu nhiên rồi chỉ xóa database đó; user test cần CREATEDB. Test catalog dùng schema riêng. Thiếu TEST_DATABASE_URL thì integration test skip.

```powershell
cd homate-agent/apps/web
npm.cmd run build
npx.cmd playwright test
```

Playwright cần backend cổng 8000 và Microsoft Edge; kiểm tra đăng nhập, các màn hình và điều khiển thiết bị qua reload. API chính: /api/auth, /api/dashboard; WebSocket: /ws/devices. Chi tiết request/response xem Swagger.
