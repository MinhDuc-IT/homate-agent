# HomeMate

HomeMate là ứng dụng quản lý nhà thông minh với giao diện web, backend nghiệp vụ và trợ lý AI dạng text. Người dùng có thể theo dõi thiết bị, quản lý kịch bản/lịch tự động, xem điện năng và gửi yêu cầu bằng ngôn ngữ tự nhiên.

## Tính năng

- Đăng nhập PIN, access token/refresh cookie và phân quyền quản trị viên/thành viên.
- Dashboard, phòng, thiết bị và điều khiển thủ công; cập nhật trạng thái qua WebSocket.
- Quản lý thành viên, kịch bản, lịch một lần/lặp lại và lịch sử thực thi.
- Báo cáo điện năng theo kỳ, phòng, thiết bị và ngày tham chiếu.
- Cài đặt, nhật ký thao tác, chính sách xác nhận và giả lập trạng thái phòng.
- Trợ lý tra cứu, điều khiển thiết bị, quản lý kịch bản/lịch và tìm tài liệu. Backend tự thực hiện thao tác thường; thao tác nhạy cảm hoặc phạm vi lớn cần xác nhận theo [chính sách](docs/agent-workflow.md).
- RAG service riêng quản lý tài liệu Markdown/TXT, embedding local và retrieval có nguồn cho chat/voice. Dùng cùng PostgreSQL nhưng schema/DB role riêng; nạp tài liệu qua CLI/API, chưa có trang quản lý. Xem [hướng dẫn RAG](docs/rag.md).

Thiết bị hoạt động qua Device Gateway, chọn adapter trong bảng `device_connections`. Docker có MQTT simulator độc lập cho đủ 37 thiết bị, với profile cho từng loại; chọn adapter `mqtt` trong DB để dùng MQTT hoặc `simulator` để mô phỏng nội bộ. Backend giữ nguyên cấu hình qua restart. Điện năng được ước tính từ trạng thái/công suất. Unity WebGL đồng bộ 27 object: đèn, rèm, TV, loa, camera và quạt hút bếp. Chọn Bật âm thanh để nghe playlist của loa. Camera dùng dữ liệu minh họa; chưa kết nối phần cứng thật. Xem [luồng điều khiển và mô phỏng 3D](docs/device-simulation.md) và [thiết bị MQTT giả lập](docs/mqtt-simulation.md).

Aura trên header hỗ trợ STT/TTS local tiếng Việt bằng Sherpa-ONNX và Piper. Nhấn Aura để nói, nhấn lại để gửi; phản hồi được tự đọc và hiển thị cùng thẻ xác nhận trong header Aura. Trang Assistant dành cho chat văn bản. Micro cần HTTPS hoặc localhost; bản ghi tối đa 60 giây. Lần build Docker đầu tiên cần Internet để tải model, sau đó STT/TTS chạy local; LLM vẫn dùng provider đã cấu hình. Xem [hướng dẫn giọng nói](docs/voice.md).

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
      agent/                # LangGraph: graph, runtime, planner, validation, tools
      clients/              # LLM, backend và RAG HTTP clients
      speech/               # Điều phối STT/TTS và speech HTTP client
      api/                  # Chat, status và speech endpoints
      contracts.py          # Kiểu giao tiếp giữa các thành phần
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

Backend giữ Clean Architecture. AI service tổ chức theo thành phần agent, dùng LangGraph để điều phối các node; bootstrap nối model và các service clients. Frontend tổ chức theo màn hình, component, state và HTTP adapters.

## Tài liệu

Chat và Aura dùng workflow hội thoại LangGraph, capability registry và kế hoạch có phiên bản. `/api/ai/analyze` cung cấp phân tích chỉ đọc; bộ đánh giá gồm 28 câu tiếng Việt. Xem [hướng dẫn agent workflow](docs/agent-workflow.md).

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

Chat/Aura có hội thoại lưu phía server, hỏi rõ nhiều lượt, sửa/hủy yêu cầu, kế hoạch có phiên bản và kết quả từng bước. Chưa có memory sở thích dài hạn. Xem [agent workflow](docs/agent-workflow.md).

Backend hiện dành cho một process. Receipt chống thực thi lặp nhưng không tạo transaction nguyên tử cho mọi side effect; kịch bản có thể chạy một phần khi persistence lỗi. Chi tiết phục hồi và trạng thái xác nhận xem tài liệu AI.
