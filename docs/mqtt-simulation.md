# Thiết bị MQTT giả lập

Docker chạy ba thành phần độc lập: backend (Device Gateway), broker Mosquitto và `device-simulator`. Simulator hỗ trợ toàn bộ 37 thiết bị của catalog: đèn, rèm, điều hòa, máy sưởi, bình nóng lạnh, quạt, ổ cắm, TV, loa, camera và khóa cửa. Mặc định container chạy tất cả thiết bị (`MQTT_SIMULATED_DEVICE_IDS=all`); adapter backend được chọn riêng trong bảng `homate.device_connections`. Backend không tự đổi adapter lúc khởi động. Agent, giao diện và mô hình Unity dùng chung luồng điều khiển hiện có.

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

Chọn một nhóm thiết bị để thử:

```sql
UPDATE homate.device_connections
SET adapter = 'mqtt'
WHERE device_id IN ('curtain-living', 'ac-bed', 'fan-kitchen', 'speaker-living', 'door');
```

Nếu muốn chạy toàn bộ catalog qua MQTT, có thể dùng `UPDATE homate.device_connections SET adapter = 'mqtt';`. Để dùng lại mô phỏng nội bộ, đổi adapter thành `simulator`. Không cần restart backend khi đổi adapter; broker và các thiết bị tương ứng phải đang chạy.

Mở Nhà 3D hoặc Thiết bị và bật/tắt đèn phòng khách 1. Backend gửi lệnh qua broker, thiết bị giả lập xử lý rồi trả trạng thái. Gateway chỉ ghi thành công sau khi nhận phản hồi đúng thiết bị và `command_id`; MQTT PUBACK của broker không phải xác nhận đã thực thi.

Broker chỉ mở trong mạng Docker. Cổng `127.0.0.1:9040` là API điều khiển môi trường giả lập, không phải API sản phẩm hay kết nối từ frontend. Broker dùng anonymous cho môi trường local; khi nối phần cứng ngoài mạng Docker cần cấu hình tài khoản, ACL và TLS.

## Mô phỏng công tắc vật lý

Các lệnh dưới đây chạy được trong PowerShell và Git Bash:

```bash
docker compose exec device-simulator python control.py light-living power true
docker compose exec device-simulator python control.py light-living brightness 30
docker compose exec device-simulator python control.py light-living power false

docker compose exec device-simulator python control.py curtain-living position 40
docker compose exec device-simulator python control.py curtain-living preset open
docker compose exec device-simulator python control.py ac-bed temperature 23
docker compose exec device-simulator python control.py ac-bed mode dry
docker compose exec device-simulator python control.py fan-kitchen speed 2
docker compose exec device-simulator python control.py speaker-living volume 50
docker compose exec device-simulator python control.py cam-bed recording true
docker compose exec device-simulator python control.py door locked false
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
# Nhãn MQTT chuyển offline; thao tác báo mất kết nối và giữ trạng thái gần nhất.
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
| `homate/availability/{node-id}` | Heartbeat/Last Will của node, có danh sách device_ids | Có |

Các topic thiết bị dùng QoS 1. Thiết bị lưu tối đa 1.000 receipt gần nhất theo mã lệnh để không thực hiện lại khi nhận bản sao còn trong bộ nhớ này. Backend bỏ ack sai mã, sai thiết bị, ack retained và state không hợp lệ; báo cáo cũ đang chờ xử lý không được ghi đè trạng thái mới hơn.

`device_connections` chọn adapter theo từng thiết bị; `device_commands.id` cũng là MQTT `command_id`. API có xác thực `GET /api/dashboard/devices/{id}/commands` xem 20 lệnh gần nhất. Thay đổi từ công tắc vật lý chỉ cập nhật state, không tạo receipt giả.

## Cấu hình

`.env.example` có:

```dotenv
MQTT_SIMULATED_DEVICE_IDS=all
MQTT_SIMULATOR_ID=device-simulator
MQTT_COMMAND_TIMEOUT_SECONDS=5
DEVICE_SIMULATOR_PORT=9040
```

Có thể chọn nhóm ID trong `apps/device-simulator/devices.json`, ví dụ `MQTT_SIMULATED_DEVICE_IDS=light-living,curtain-living,ac-bed`. `all` chọn đủ 37 ID. `devices.json` chứa trạng thái ban đầu và tên profile; `profiles.json` quy định trường trạng thái, kiểu dữ liệu, khoảng giá trị và enum. Cả hai là cấu hình độc lập, không đọc DB hay import backend lúc chạy. Khi cập nhật catalog chuẩn, chạy `python tools/export_simulator_catalog.py` bằng môi trường đã cài backend để xuất lại cấu hình, sau đó chạy lại container:

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
.venv/Scripts/python.exe tools/test_mqtt_catalog.py
```

`test_mqtt_catalog.py` thử từng control của cả 37 thiết bị qua MQTT, kiểm tra receipt và trạng thái từ công tắc vật lý qua WebSocket. Script tạm đổi adapter sang MQTT, cuối cùng khôi phục adapter, trạng thái backend và trạng thái phần cứng giả lập; bản sao trước khi thử được lưu trong `.work/mqtt-catalog-backup.json`. Các receipt thử nghiệm vẫn được giữ trong lịch sử lệnh.

Bộ integration dùng tài khoản demo Minh Đức/PIN 1234, gọi backend và simulator local, không gọi LLM. Kiểm tra ack, receipt, công tắc vật lý qua WebSocket, từ chối, timeout, độ trễ quá hạn và health trong lúc chờ; cuối cùng trả chế độ về normal và khôi phục trạng thái thiết bị.

## Profile và phạm vi mô phỏng

| Thiết bị | Trạng thái hiện hỗ trợ |
|---|---|
| Đèn | `power`, `brightness` nếu catalog có dimmer |
| Rèm | `position`, `preset`; công tắc vật lý đồng bộ hai trường |
| Điều hòa | `power`, `temperature`, `mode`; `fan` nếu có control |
| Máy sưởi / bình nóng lạnh | `power`, `temperature` theo giới hạn riêng |
| Quạt | `speed` theo các cấp của từng thiết bị |
| Ổ cắm / TV | `power` |
| Loa | `power`, `volume` |
| Camera | `recording` |
| Khóa cửa | `locked`; backend chuyển thao tác `lock`/`unlock` thành desired state |

Mỗi thiết bị có hàng đợi lệnh riêng, giữ thứ tự của thiết bị đó. `mode`, `delay_ms`, timeout, chống chạy lặp, lưu trạng thái và ACK dùng chung cho các profile. Dùng cú pháp rõ ràng `python control.py --fault ac-bed mode silent` để giả lập lỗi; `python control.py ac-bed mode dry` đổi chế độ điều hòa. Cú pháp lỗi cũ `mode normal|silent|reject` và `delay_ms` vẫn được hỗ trợ.

Phần cứng giả lập kiểm tra trạng thái đầy đủ theo profile, ACK sau khi lưu kết quả; không mô phỏng vật lý nhiệt độ phòng, độ trễ động cơ rèm, video camera hay dịch vụ nhạc. Các hiệu ứng hình ảnh/âm thanh hiện có vẫn do Unity thực hiện từ trạng thái backend. Các điều kiện control, quyền và conflict vẫn do backend kiểm tra; thay đổi vật lý báo lại thực trạng, không tự tạo lệnh khác.

Trạng thái đã lưu trong volume được giữ nguyên, không bị reset về giá trị mặc định khi khởi động. Thiết bị mới bắt đầu tắt, quạt ở cấp 0, rèm đóng, camera ngừng ghi và cửa khóa. Đổi adapter không sao chép trạng thái giữa hai bộ mô phỏng: đợi report tiếp theo hoặc gửi thao tác để đồng bộ. Các thiết bị cùng node hiện dùng chung kết nối online/offline.

## Chạy nhiều node

Không cần copy source. Có thể thêm service Compose dùng chung image, cấu hình nhóm `MQTT_SIMULATED_DEVICE_IDS` riêng, `MQTT_SIMULATOR_ID` khác nhau, volume `/data` riêng và cổng host khác nhau nếu expose HTTP. Một device ID chỉ được giao cho một node; không chạy hai node cùng nhận lệnh cho một thiết bị. Dừng một node chỉ làm các thiết bị thuộc node đó offline.


Đây là giao thức demo của HomeMate. Khi nối thiết bị thương mại, thêm adapter ánh xạ topic/payload riêng thay vì giả định mọi thiết bị MQTT dùng giao thức này. Backend hiện chạy một worker; chưa hỗ trợ nhiều backend đồng thời điều phối cùng thiết bị.
## Theo dõi kết nối thiết bị

Backend theo dõi availability riêng với trạng thái bật/tắt. Thiết bị giả lập gửi heartbeat mỗi 10 giây lên `homate/availability/device-simulator`, gồm `device_ids`, `online` và `sent_at` (Unix timestamp). MQTT Last Will phát `online: false` khi container mất kết nối. Thiết bị MQTT khác có thể dùng topic `homate/availability/{client-id}` cùng hợp đồng dữ liệu.

Không có heartbeat trong 35 giây được xem là mất kết nối. Backend mất kết nối broker cũng làm các thiết bị MQTT hiển thị offline. Khi chưa nhận được thông tin còn hiệu lực, trạng thái là chưa rõ kết nối. Timestamp yêu cầu đồng hồ thiết bị và backend đồng bộ. Trạng thái kết nối nằm trong bộ nhớ, được khôi phục từ availability còn hiệu lực và heartbeat sau restart.

Giao diện lấy trạng thái qua API có xác thực `GET /api/dashboard/device-connectivity` mỗi 3 giây. Danh sách thiết bị, chi tiết phòng và bảng điều khiển 3D hiển thị trạng thái MQTT cùng lần cuối liên lạc. Simulator nội bộ không phụ thuộc mạng nên không hiện cảnh báo MQTT. Khi offline, trạng thái bật/tắt vẫn là lần ghi nhận gần nhất.

Lệnh tới thiết bị đã biết offline bị từ chối, không publish và không thay đổi trạng thái. Nếu chưa rõ kết nối hoặc thiết bị im lặng dù heartbeat vẫn còn, backend chờ ACK rồi trả timeout. Lệnh thất bại không được tự gửi lại khi thiết bị online; trạng thái thực tế được đồng bộ qua report.

Để thử, đặt adapter đèn `light-living` thành `mqtt` theo hướng dẫn cấu hình DB ở trên, mở trang thiết bị rồi chạy `docker compose stop device-simulator`. Quan sát nhãn mất kết nối và thử bật/tắt. Chạy `docker compose start device-simulator` để kiểm tra kết nối trở lại. Việc phát hiện qua Last Will phụ thuộc broker phát hiện disconnect; nếu không nhận được Last Will, heartbeat hết hạn sau 35 giây.

Chạy `python tools/test_device_connectivity.py` để kiểm tra tự động mất kết nối thiết bị và broker, chặn lệnh offline, giữ trạng thái gần nhất và nhận kết nối trở lại. Bài thử tạm chọn adapter MQTT rồi khôi phục cấu hình DB ban đầu; không gọi LLM.
