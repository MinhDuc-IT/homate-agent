# Điều khiển thiết bị và mô phỏng 3D

## Luồng thực thi

```text
Giao diện / agent / lịch / kịch bản
  → DeviceStore: kiểm tra control, giá trị, điều kiện và conflict
  → DeviceGateway: chọn adapter theo device_connections
  → SimulatorAdapter hoặc MQTT → broker → thiết bị giả lập → phản hồi trạng thái
  → PostgreSQL: lưu reported state và receipt thành công trong cùng transaction
  → DeviceStore + WebSocket
  → DevicesContext → Unity bridge → mô hình đèn/rèm
```

`devices.controls` tiếp tục là mô tả khả năng của thiết bị; không tạo thêm một schema capability song song. Unity chỉ hiển thị trạng thái, không gửi lệnh MQTT/HTTP và không giữ trạng thái thay backend. Các thao tác qua agent vẫn phải qua kiểm tra quyền và policy hiện có trước khi vào DeviceStore.

## Kết nối và kết quả lệnh

Migration `0007` thêm:

- `homate.device_connections`: adapter và settings của từng thiết bị, được quản lý trực tiếp trong DB. Backend không tự thay đổi kết nối hiện có khi khởi động; thiết bị chưa có kết nối được tạo với adapter `simulator`.
- `homate.device_commands`: desired state, reported state, adapter, thời điểm và kết quả của từng lần dispatch.

Trạng thái lệnh: `processing`, `succeeded`, `failed`, `interrupted`. Khi backend khởi động lại, lệnh còn processing được đánh dấu interrupted; không tự gửi lại. API có xác thực `GET /api/dashboard/devices/{id}/commands` trả 20 lệnh gần nhất trong nhà của người dùng.

Simulator hiện phản hồi tức thì. Chỉ sau khi trạng thái được xác nhận và lưu thành công, bộ nhớ và giao diện mới được cập nhật. Adapter không tồn tại hoặc báo trạng thái khác yêu cầu sẽ làm lệnh thất bại, giữ nguyên trạng thái thiết bị. `set_state` dành cho báo cáo trạng thái, không dispatch lại lệnh để tránh vòng lặp.

Gateway chờ phản hồi thiết bị trong worker thread; MQTT có network thread riêng và task đối soát báo cáo để không tạo vòng lặp lệnh. Có timeout, kết nối lại và chống chạy lặp ở thiết bị giả lập. Backend vẫn giới hạn một process với DeviceStore; chưa có điều phối nhiều backend, adapter giao thức hãng cụ thể, tự retry lệnh hay mô phỏng nhiệt độ phòng. Publish MQTT thành công chưa phải thiết bị thực hiện thành công.

## Unity WebGL

Build lấy 18 binding đèn/rèm từ snapshot danh mục CASA và kiểm tra tên object là duy nhất. Scene gốc được giữ nguyên; component mới chỉ được thêm vào scene sinh ra khi build.

- 13 nhóm đèn: cập nhật Light, cường độ theo brightness và vật liệu phát sáng đã có emission.
- 5 rèm: lấy mẫu clip mở rèm gốc theo position 0–100%, tắt Animator cũ để không ghi đè trạng thái.
- 6 camera: LED ghi hình đỏ nhấp nháy khi recording=true, tắt khi không ghi. Đây là chỉ báo trạng thái mô phỏng, chưa có video ghi hình thật.
- TV: màn hình đen khi tắt, bảng màu minh họa khi bật. Không thay đổi khung và chân TV, chưa phát video/đổi kênh.
- Loa: đèn nguồn và các vòng sóng âm thay đổi theo power/volume; volume=0 không có sóng âm. Playlist gốc được phát khi người dùng bật âm thanh mô phỏng.
- Quạt hút bếp: đèn báo và hạt chuyển động hướng lên cửa hút; speed=0 dừng, cấp 1–3 thay đổi tốc độ và mật độ. Không quay cả vỏ máy vì model không có cánh quạt tách rời.

Tổng cộng 27 binding có hiệu ứng. 10 thiết bị chưa có model vẫn giữ trạng thái phần mềm, không gán vào object khác. Các camera dùng source_ref của prefab để tránh nhầm với Camera_SALON/Camera_HABITACION dùng quan sát scene. Menu Xem thiết bị đưa góc nhìn tới TV, loa, quạt hút và từng model camera để dễ quan sát hiệu ứng.

Âm thanh loa được stream bằng HTMLAudioElement từ `/unity/audio/`, tách khỏi bộ nhớ WebAssembly. Build sao chép ba MP3 gốc sang các tên track cố định; các bản sao build được ignore trong Git. Không tự phát khi mở trang: nhấn Bật âm thanh để cho phép phát, rồi điều khiển power/volume của loa như bình thường. Tắt âm thanh chỉ tắt phát tại trình duyệt, không đổi trạng thái loa trong backend. Trình duyệt chặn phát hoặc tải nhạc lỗi sẽ trả nút về trạng thái cho phép thử lại. Playlist chuyển bài và lặp, không khởi động lại khi thiết bị khác cập nhật trạng thái. Phản hồi TTS của trợ lý là luồng riêng.

Cửa sổ phòng ngủ có hai lớp: `curtain-bed-roller` (rèm cuốn) và `curtain` (rèm ngoài). Muốn quan sát rèm ngoài, mở rèm cuốn trước. Camera phòng mặc định nhìn vào nội thất; kéo để quay về cửa sổ khi kiểm tra rèm.

Frontend gửi snapshot hiện tại sau khi Unity báo ready và mỗi khi DevicesContext thay đổi, gồm power, brightness, position, recording, volume và speed. Snapshot WebSocket khi reconnect khôi phục trạng thái mới nhất. Bridge kiểm tra origin và cửa sổ gửi; Unity chỉ nhận các ID đã được bind trong build. `deviceSync` trong build-status chỉ có giá trị true ở bản build hỗ trợ đồng bộ; syncKinds và focusDevices mô tả khả năng bản build đang phục vụ.

## Chạy và kiểm tra

```powershell
docker compose build backend
docker compose run --rm --no-deps backend alembic upgrade head
docker compose up -d --no-deps backend
./tools/build_unity.ps1 -UnityEditor 'I:\Program Files\Unity\Hub\Editor\6000.0.38f1\Editor\Unity.exe'
docker compose up -d --build --no-deps web
```

Mở Nhà 3D, chọn góc nhìn phù hợp rồi điều khiển thiết bị từ giao diện hoặc agent. Có thể mở trang Thiết bị cạnh mô hình để dễ quan sát. Thử bật/tắt TV, đổi trạng thái ghi hình camera, bật loa và đổi volume, đổi cấp quạt hút; tải lại trang vẫn lấy đúng trạng thái backend. Các lệnh tương ứng từ agent và lịch đi qua cùng Gateway.
# Điều khiển trực tiếp trong mô hình

Bấm vào thiết bị trong mô hình để chọn. Thiết bị được đánh dấu bằng khung xanh; bảng bên cạnh hiển thị tên, trạng thái và các điều khiển hỗ trợ. Có thể chọn nhanh cả 27 thiết bị đã ánh xạ bằng danh sách **Xem thiết bị**. Bấm vùng trống hoặc nút đóng để bỏ chọn. Kéo để xoay sẽ không được tính là bấm chọn.

Các nút dùng chung API thiết bị và Device Gateway với giao diện điều khiển thông thường. Mô hình chỉ cập nhật hiệu ứng theo trạng thái backend trả về; chọn thiết bị không tự thay đổi trạng thái.

Cuộn chuột hoặc dùng nút **+ / −** để phóng to, thu nhỏ. Ở toàn cảnh, camera tiến gần hoặc lùi khỏi tâm ngôi nhà; trong phòng, camera di chuyển tiến/lùi theo hướng đang nhìn. Kéo chuột trái để xoay, kéo chuột phải để dịch chuyển góc nhìn. Chọn lại phòng hoặc **Toàn cảnh** để trở về vị trí mặc định.

## MQTT giả lập độc lập

Trong Compose, container `device-simulator` có thể thực thi lệnh cho đèn phòng khách 1 qua broker `mqtt` khi adapter của đèn trong DB là `mqtt`. Unity vẫn chỉ nhận trạng thái backend đã báo cáo. Công tắc vật lý giả lập phát MQTT state để cập nhật backend và mô hình; khi adapter là `simulator`, báo cáo MQTT của đèn bị bỏ qua. Xem [hướng dẫn và kịch bản MQTT](mqtt-simulation.md).
