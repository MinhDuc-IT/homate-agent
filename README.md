# HomeMate

HomeMate là ứng dụng quản lý nhà thông minh với giao diện web, backend nghiệp vụ và trợ lý AI dạng text. Người dùng có thể theo dõi thiết bị, quản lý kịch bản/lịch tự động, xem điện năng và gửi yêu cầu bằng ngôn ngữ tự nhiên.

## Tính năng

- Đăng nhập PIN, access token/refresh cookie và phân quyền quản trị viên/thành viên.
- Dashboard, phòng, thiết bị và điều khiển thủ công; cập nhật trạng thái qua WebSocket.
- Quản lý thành viên, kịch bản, lịch một lần/lặp lại và lịch sử thực thi.
- Báo cáo điện năng theo kỳ, phòng, thiết bị và ngày tham chiếu.
- Cài đặt, nhật ký thao tác, chính sách xác nhận và giả lập trạng thái phòng.
- Trợ lý text với 17 tools: tra cứu, điều khiển thiết bị, quản lý kịch bản và lịch. Thao tác thay đổi dữ liệu cần người dùng xác nhận.

Thiết bị hiện hoạt động ở chế độ mô phỏng; điện năng được ước tính từ trạng thái/công suất. Camera dùng dữ liệu minh họa. Kết nối phần cứng, STT/TTS và RAG chưa triển khai; viewport 3D cần bản Unity WebGL phù hợp.

## Bắt đầu nhanh

Cần Docker Desktop đang chạy với Linux containers. Từ thư mục project:

```powershell
# Chỉ tạo .env nếu chưa có; giữ cấu hình/key bạn đã điền.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
```

Để dùng OpenRouter, đặt trong `.env`:

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-private-key
OPENROUTER_MODEL_NAME=openai/gpt-4o-mini
```

Đăng nhập mẫu: **Minh Đức / PIN 1234**. Dữ liệu phát triển gồm nhà Michelin Bois, 6 phòng, 22 thiết bị và 4 thành viên.

| Thành phần | Địa chỉ |
|---|---|
| Giao diện | http://localhost:5173 |
| Trợ lý | http://localhost:5173/assistant |
| Backend Swagger | http://localhost:8000/docs |
| AI Swagger | http://localhost:8010/docs |
| PostgreSQL trên máy host | localhost:55433 |

Backend tự chạy Alembic trước khi khởi động. Volume `postgres_data` giữ dữ liệu khi chạy `docker compose down`. Sau khi đổi provider/key trong `.env`, áp dụng bằng `docker compose up -d --force-recreate ai-service`.

## Kiến trúc

```mermaid
flowchart LR
    Web[React frontend] --> Backend[FastAPI backend]
    Web --> AI[AI service]
    AI --> Provider[LLM provider]
    AI -->|Tools với token người dùng| Backend
    Backend --> DB[(PostgreSQL)]
    Backend -->|WebSocket| Web
```

Backend sở hữu dữ liệu, phân quyền, validation và thực thi. AI service diễn giải yêu cầu và đề xuất thao tác qua HTTP, không truy cập trực tiếp database. Xác nhận từ giao diện gọi backend trực tiếp.

```text
apps/
  backend/
    src/homate/
      application/          # Use cases và repository ports
      modules/              # Home, identity, automation, energy
      presentation/         # HTTP/auth/WebSocket
      infrastructure/       # PostgreSQL, tokens, weather, realtime
      software_bootstrap.py # Composition root
      worker.py             # Lịch, lấy mẫu điện năng, quy tắc phòng trống
    migrations/
    tests/
  ai-service/
    src/homate_ai/
      domain/
      application/          # Orchestrator, tools, ports
      infrastructure/       # LLM và backend HTTP adapters
      presentation/
      bootstrap.py
    tests/
  web/
    src/
      screens/, components/
      api/, context/, hooks/, types/, config/
    tests/
docs/
compose.yaml
```

Domain/application độc lập HTTP và database adapters. Infrastructure hiện thực các port; composition root nối các thành phần. Frontend tổ chức theo màn hình, component, state và HTTP adapters.

## Tài liệu

- [Cài đặt, cấu hình, chạy local và Docker](docs/getting-started.md)
- [Kiến trúc AI, tools, memory và xác nhận](docs/ai-architecture.md)

## Kiểm thử

Cài dependencies Python theo hướng dẫn local, sau đó:

```powershell
# Backend: PostgreSQL thật, user test cần quyền CREATEDB.
cd apps/backend
$env:TEST_DATABASE_URL = "postgresql+psycopg://homate:homate_local@127.0.0.1:55433/homate"
..\..\.venv\Scripts\python.exe -m pytest -q

# AI: model/provider giả lập, không gọi LLM thật.
cd ../ai-service
..\..\.venv\Scripts\python.exe -m pytest -q

# Frontend: backend local phải chạy ở cổng 8000; cần Microsoft Edge.
cd ../web
npm.cmd ci
npm.cmd run build
npx.cmd playwright test
```

Không có `TEST_DATABASE_URL`, integration tests backend được skip. Các test tạo database/schema riêng và dọn dữ liệu test khi kết thúc. Playwright giả lập phản hồi chat nhưng gọi backend thật để kiểm tra proposal và thực thi.

## Phạm vi hiện tại

Agent dùng ngữ cảnh tối đa 12 tin nhắn gần nhất do frontend gửi; lịch sử mất khi reload/rời trang chat. Chưa có memory bền vững hoặc planner bảo đảm chuỗi thao tác tự do. Các trường hợp mơ hồ/thiếu thông tin dựa vào LLM hỏi lại, cần đánh giá bằng bộ câu thực tế.

Backend hiện dành cho một process. Receipt chống thực thi lặp nhưng không tạo transaction nguyên tử cho mọi side effect; kịch bản có thể chạy một phần khi persistence lỗi. Chi tiết phục hồi và trạng thái xác nhận xem tài liệu AI.
