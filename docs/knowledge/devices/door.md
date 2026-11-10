# Hướng dẫn mô phỏng: Cửa chính

Cửa chính tại Phòng khách (door) nằm tại Phòng khách, nhóm Khóa cửa trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Cửa chính

Cửa chính tại Phòng khách (door): Mở khóa cửa [unlock] hỗ trợ thực hiện thao tác mở khóa cửa. Đây là thao tác được đánh dấu nhạy cảm trong cấu hình.

Cửa chính tại Phòng khách (door): Đóng khóa cửa [lock] hỗ trợ thực hiện thao tác đóng khóa cửa.

## Cách thao tác với Cửa chính

Với Cửa chính tại Phòng khách (door), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Cửa chính tại Phòng khách (door), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Cửa chính

Với Cửa chính tại Phòng khách (door), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Cửa chính tại Phòng khách (door) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: a4896daf6b21092ba698e8bd8a86d66d00cbba4225c0b53365760251b7c040b7.
