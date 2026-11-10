# Hướng dẫn mô phỏng: Camera ban công

Camera ban công (cam-balcony) nằm tại Ban công, nhóm Camera trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Camera ban công

Camera ban công (cam-balcony): Ghi hình [recording] hỗ trợ bật/tắt ghi hình mô phỏng.

Camera ban công (cam-balcony): control recording chỉ thay đổi trạng thái ghi hình mô phỏng. Camera hiện dùng dữ liệu minh họa; bật recording không chứng minh đã có video thật được lưu. Chưa có tài liệu thời hạn lưu, thẻ nhớ, độ phân giải hay kết nối camera vật lý.

## Cách thao tác với Camera ban công

Với Camera ban công (cam-balcony), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Camera ban công (cam-balcony), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Camera ban công

Với Camera ban công (cam-balcony), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Camera ban công (cam-balcony) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 475217eb0677241adf4ba626c78e822b7043c16c2b2a1415eacb9b0b68d48f29.
