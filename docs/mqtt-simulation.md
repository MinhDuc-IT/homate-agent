# Thiết bị MQTT giả lập

Docker chạy ba thành phần độc lập: backend (Device Gateway), broker Mosquitto và `device-simulator`. Thiết bị giả lập mặc định là **Đèn phòng khách 1** (`light-living`); adapter backend được chọn riêng trong bảng `homate.device_connections`. Backend không tự đổi adapter lúc khởi động. Agent, giao diện và mô hình Unity không cần biết loại kết nối.

## Khởi động

```bash
docker compose up -d --build
docker compose ps
```

Nếu DB chưa cấu hình MQTT, chạy SQL sau trong pgAdmin:

```sql
UPDATE homate.device_connections
SET adapter = 'mqtt', settings = '{}'::jsonb
WHERE device_id = 'light-living';
```

Mở Nhà 3D hoặc Thiết bị và bật/tắt đèn phòng khách 1. Backend gửi lệnh qua broker, thiết bị giả lập xử lý rồi trả trạng thái. Gateway chỉ ghi thành công sau khi nhận phản hồi đúng thiết bị và `command_id`; MQTT PUBACK của broker không phải xác nhận đã thực thi.

Broker chỉ mở trong mạng Docker. Cổng `127.0.0.1:9040` là API điều khiển môi trường giả lập, không phải API sản phẩm hay kết nối từ frontend. Broker dùng anonymous cho môi trường local; khi nối phần cứng ngoài mạng Docker cần cấu hình tài khoản, ACL và TLS.

## Mô phỏng công tắc vật lý

Các lệnh dưới đây chạy được trong PowerShell và Git Bash:

```bash
docker compose exec device-simulator python control.py light-living power true
docker compose exec device-simulator python control.py light-living brightness 30
docker compose exec device-simulator python control.py light-living power false
```

Lệnh này thay đổi trạng thái trong thiết bị giả lập, **không gọi backend**. Thiết bị phát MQTT state, backend nhận và lưu trạng thái, sau đó phát WebSocket để giao diện và mô hình cập nhật. Không tạo thêm lệnh điều khiển và không gửi lệnh ngược lại thiết bị.

## Thử tình huống lỗi

```bash
# Không phản hồi lệnh: thao tác từ giao diện sẽ timeout.
docker compose exec device-simulator python control.py light-living mode silent

# Từ chối lệnh ngay.
docker compose exec device-simulator python control.py light-living mode reject

# Phản hồi chậm 6,5 giây, quá timeout mặc định 5 giây.
docker compose exec device-simulator python control.py light-living delay_ms 6500

# Trở lại bình thường, đồng thời xóa độ trễ.
docker compose exec device-simulator python control.py light-living mode normal
```

Các chế độ này chỉ tác động đến lệnh MQTT. Công tắc vật lý giả lập vẫn dùng được. Thiết bị kiểm tra hạn lệnh sau khi chờ độ trễ và không thực hiện lệnh đã hết hạn. Khi timeout, backend không ghi trạng thái mong muốn thành thành công và không tự gửi lại; thiết bị thực tế vẫn là nguồn trạng thái cuối cùng nếu có báo cáo đến muộn.

Thử mất kết nối:

```bash
docker compose stop device-simulator
# Thao tác từ giao diện: phải báo không thực hiện được sau timeout.
docker compose start device-simulator

docker compose restart mqtt
```

Client tự kết nối lại, đăng ký lại topic và công bố lại trạng thái. Trạng thái thiết bị và bộ chống chạy lặp được lưu trong volume `mqtt_device_data`; broker lưu retained state trong `mqtt_data`. Không xóa volume nếu muốn giữ trạng thái.

## Giao thức local

| Topic | Vai trò | Retained |
|---|---|---|
| `homate/devices/{id}/set` | Backend gửi `command_id`, `device_id`, `expires_at`, `desired_state` đầy đủ | Không |
| `homate/devices/{id}/ack` | Thiết bị phản hồi `command_id`, `status`, state và phiên bản nếu thành công | Không |
| `homate/devices/{id}/state` | Trạng thái đầy đủ kèm `device_id`, `boot_id`, `revision` | Có |
| `homate/simulator/availability` | Online/offline của node giả lập, có Last Will | Có |

Các topic thiết bị dùng QoS 1. Thiết bị lưu tối đa 1.000 receipt gần nhất theo mã lệnh để không thực hiện lại khi nhận bản sao còn trong bộ nhớ này. Backend bỏ ack sai mã, sai thiết bị, ack retained và state không hợp lệ; báo cáo cũ đang chờ xử lý không được ghi đè trạng thái mới hơn.

`device_connections` chọn adapter theo từng thiết bị; `device_commands.id` cũng là MQTT `command_id`. API có xác thực `GET /api/dashboard/devices/{id}/commands` xem 20 lệnh gần nhất. Thay đổi từ công tắc vật lý chỉ cập nhật state, không tạo receipt giả.

## Cấu hình

`.env.example` có:

```dotenv
MQTT_SIMULATED_DEVICE_IDS=light-living
MQTT_COMMAND_TIMEOUT_SECONDS=5
DEVICE_SIMULATOR_PORT=9040
```

Có thể chọn thêm đèn trong `apps/device-simulator/devices.json`, ví dụ `MQTT_SIMULATED_DEVICE_IDS=light-living,light-balcony`. File này là cấu hình thiết bị giả lập độc lập, không đọc DB của backend. Các ID và khóa state phải khớp thiết bị backend. Chạy lại:

```bash
docker compose up -d --build backend device-simulator
```

`MQTT_SIMULATED_DEVICE_IDS` chỉ cấu hình các thiết bị có trong container giả lập, không cập nhật DB backend. Mỗi adapter phải được chọn trong `homate.device_connections`. Chuyển về simulator nội bộ:

```sql
UPDATE homate.device_connections
SET adapter = 'simulator', settings = '{}'::jsonb
WHERE device_id = 'light-living';
```

Thay đổi có hiệu lực cho thao tác tiếp theo, không cần restart backend. Khi adapter là `simulator`, các báo cáo MQTT của thiết bị đó bị bỏ qua. Chuyển sang `mqtt` cho thiết bị đã có trong catalog cũng không cần restart nếu backend đã cấu hình `MQTT_HOST`; chờ báo cáo tiếp theo hoặc gửi lệnh để đối soát trạng thái. Dữ liệu adapter/settings hiện có, kể cả metadata `managed_by` cũ, được giữ nguyên qua restart. DB mới vẫn tạo kết nối `simulator` cho thiết bị chưa có kết nối.

`MQTT_HOST` chỉ bật/tắt kết nối broker, không thay đổi adapter trong DB. Nếu DB chọn MQTT nhưng backend chưa cấu hình broker hoặc thiết bị không chạy, thao tác sẽ thất bại thay vì tự chuyển về simulator.

## Kiểm thử

```bash
.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mqtt.py -q
.venv/Scripts/python.exe tools/test_mqtt_simulation.py
```

Bộ integration dùng tài khoản demo Minh Đức/PIN 1234, gọi backend và simulator local, không gọi LLM. Kiểm tra ack, receipt, công tắc vật lý qua WebSocket, từ chối, timeout, độ trễ quá hạn và health trong lúc chờ; cuối cùng trả chế độ về normal và khôi phục trạng thái thiết bị.

Đây là giao thức demo của HomeMate. Khi nối thiết bị thương mại, thêm adapter ánh xạ topic/payload riêng thay vì giả định mọi thiết bị MQTT dùng giao thức này. Backend hiện chạy một worker; chưa hỗ trợ nhiều backend đồng thời điều phối cùng thiết bị.
