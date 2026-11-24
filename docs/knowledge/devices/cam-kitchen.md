# Hướng dẫn mô phỏng: Camera bếp

Camera bếp (cam-kitchen) nằm tại Bếp, nhóm Camera trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Camera bếp

Camera bếp (cam-kitchen): Ghi hình [recording] hỗ trợ bật/tắt ghi hình mô phỏng.

Camera bếp (cam-kitchen): control recording chỉ thay đổi trạng thái ghi hình mô phỏng. Camera hiện dùng dữ liệu minh họa; bật recording không chứng minh đã có video thật được lưu. Chưa có tài liệu thời hạn lưu, thẻ nhớ, độ phân giải hay kết nối camera vật lý.

## Cách thao tác với Camera bếp

Với Camera bếp (cam-kitchen), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Camera bếp (cam-kitchen), nêu rõ tên/phòng và giá trị muốn đặt. Thao tác thông thường có thể thực hiện ngay khi yêu cầu đã rõ và hợp lệ. Với thao tác cần xác nhận hoặc có xung đột, kiểm tra đề xuất trước khi đồng ý; có thể từ chối nếu sai thiết bị hoặc giá trị. Nếu đề xuất hết hạn, hãy gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Camera bếp

Với Camera bếp (cam-kitchen), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Camera bếp (cam-kitchen) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: b9800440fec8dbe3c1d9f29154cefe50cee1d9f7a06ba10d381d13b698303157.
