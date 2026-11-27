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

STT/TTS tiếng Việt chạy local bằng `speech-service`, được khởi động cùng Compose. Khi phát triển local, chạy thêm service ở port 9020 theo [hướng dẫn giọng nói](voice.md).

Compose cũng chạy broker `mqtt` và `device-simulator`. Chọn adapter `mqtt` cho đèn phòng khách 1 trong bảng `homate.device_connections` để thử giao tiếp MQTT; backend không tự thay đổi adapter lúc khởi động. Có thể mô phỏng công tắc vật lý bằng `docker compose exec device-simulator python control.py light-living power true`. Xem [hướng dẫn MQTT](mqtt-simulation.md) để cấu hình DB và thử timeout, phản hồi chậm, mất kết nối.

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

## Bản xem nhà 3D

Source Unity nằm ở `apps/unity-sim`, scene gốc `Assets/Scenes/CASA.unity`. Màn hình `/house-3d` chỉ mở Unity khi có bản build hoàn tất. Bản build mới đồng bộ trạng thái toàn bộ 27 object đã có mapping: đèn, rèm, TV, loa, camera và quạt hút bếp. Dùng Xem thiết bị để nhìn cận cảnh các hiệu ứng mới; chọn Bật âm thanh để nghe playlist khi loa bật. Xem [luồng điều khiển và mô phỏng](device-simulation.md).

Thanh góc nhìn cho phép chuyển nhanh giữa toàn cảnh, phòng khách, phòng ngủ, phòng bếp và cửa vào. Các góc phòng lấy từ camera có sẵn trong scene. Trong phòng, kéo chuột để nhìn quanh tại chỗ và cuộn để đổi mức phóng đại; chọn Toàn cảnh để trở lại chế độ xoay quanh nhà. Nút chọn góc nhìn chỉ bật sau khi mô hình tải xong.

Danh mục demo lấy scene CASA làm chuẩn: 4 phòng (`living`, `bed`, `kitchen`, `bath`), 37 thiết bị, trong đó 27 thiết bị có object 3D tương ứng: 13 nhóm đèn, 5 bộ rèm, 6 camera, TV, loa và quạt hút bếp. 10 thiết bị còn lại vẫn là mô phỏng phần mềm, chưa có model được xác minh. Đồ nội thất và các đồ gia dụng khác chỉ là vật trang trí, chưa tự động trở thành thiết bị thông minh.

Các thiết bị chưa có model: `ac-living`, `ac-bed`, `ac-office`, `heater-living`, `heater-bath`, `door`, `fan-bed`, `fan-bath`, `plug-kitchen`, `plug-office`. Không gán chúng vào object khác chỉ vì có tên hoặc vị trí gần giống.

API có xác thực `GET /api/dashboard/simulation` trả về danh sách binding và trạng thái `mapped`/`unmapped`. `mapped` xác nhận đã xác định được object; `sync_kinds` liệt kê nhóm có hỗ trợ đồng bộ (light, curtain, camera, tv, speaker, fan). Marker `build-status.json` xác định khả năng của bản WebGL đang phục vụ. Binding giữ cả tên object và tham chiếu gốc (`game_object:<fileID>` hoặc `prefab_instance:<fileID>`) để phân biệt model camera với camera dùng để quan sát scene. Các tham chiếu này thuộc `Assets/Scenes/CASA.unity`, không phải ID của scene sinh ra khi build.

Migration `0006` chuyển thiết bị và số liệu điện năng của khu làm việc/ban công cũ về phòng khách, giữ ID, trạng thái, control, kịch bản và lịch. Một số tên demo được cập nhật theo nhóm đèn/camera trong scene; tên do người dùng tự đặt được giữ. Các ID cũ như `light-office`, `light-balcony`, `cam-balcony`, `ac-office`, `plug-office` vẫn được giữ để không làm đứt tham chiếu. Migration lưu snapshot trước thay đổi trong `homate.simulation_catalog_migrations` và chỉ hỗ trợ nâng cấp; muốn hoàn tác toàn bộ cần khôi phục bản sao lưu PostgreSQL trước migration. Không dùng `docker compose down -v` để cập nhật danh mục.

Mở project bằng Unity Editor 6000.0.38f1 có WebGL Build Support, kích hoạt license trong Unity Hub. Từ PowerShell tại thư mục gốc project:

```powershell
./tools/build_unity.ps1 -UnityEditor 'I:\Program Files\Unity\Hub\Editor\6000.0.38f1\Editor\Unity.exe'
docker compose up -d --build web
```

Script tạo bản sao scene để build; không sửa scene gốc. Bản xem gỡ logic MQTT/UDP/avatar cũ khỏi scene build, ẩn UI Unity cũ, tắt âm thanh và bỏ component bị thiếu script trong bản sao. Các tham chiếu asset thiếu khác vẫn cần kiểm tra trong Unity Editor. Log build nằm ở `.work/unity-webgl.log`; binary WebGL và cache Unity không đưa vào Git. Docker chỉ phục vụ bản WebGL đã build, không tự chạy Unity Editor. Script đặt cache package/build và file tạm trong `.work` trên cùng ổ với project. Đặt thư mục Editor và module trên ổ I trong Hub trước khi cài; Hub/Windows vẫn có thể tạo dữ liệu cấu hình trong hồ sơ người dùng.

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
