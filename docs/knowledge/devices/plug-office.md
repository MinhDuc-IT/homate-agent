# Hướng dẫn mô phỏng: Ổ máy tính

Ổ máy tính tại Phòng làm việc (plug-office) nằm tại Phòng làm việc, nhóm Ổ cắm trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Ổ máy tính

Ổ máy tính tại Phòng làm việc (plug-office): Nguồn [power] hỗ trợ bật/tắt nguồn.

## Cách thao tác với Ổ máy tính

Với Ổ máy tính tại Phòng làm việc (plug-office), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Ổ máy tính tại Phòng làm việc (plug-office), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Ổ máy tính

Với Ổ máy tính tại Phòng làm việc (plug-office), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Ổ máy tính tại Phòng làm việc (plug-office) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: d69a35f61f58583004db05e6838d1bb23e19c9f8d246cf8d5dd95acdc46b152c.
