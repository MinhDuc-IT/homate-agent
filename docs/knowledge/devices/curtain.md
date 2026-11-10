# Hướng dẫn mô phỏng: Rèm phòng ngủ

Rèm phòng ngủ (curtain) nằm tại Phòng ngủ, nhóm Rèm trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Rèm phòng ngủ

Rèm phòng ngủ (curtain): Mức mở [preset] hỗ trợ chọn một trong: Đóng (closed); Mở hé (ajar); Mở hết (open).

Rèm phòng ngủ (curtain): Vị trí [position] hỗ trợ giá trị từ 0 đến 100 %.

Rèm phòng ngủ (curtain): position=0% là đóng, position=100% là mở hết; vị trí ở giữa tương ứng mở hé. Dùng phần trăm vị trí để chỉ định mức mở cụ thể; không suy ra thời gian chạy motor hoặc kích thước rèm từ giá trị này.

## Cách thao tác với Rèm phòng ngủ

Với Rèm phòng ngủ (curtain), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Rèm phòng ngủ (curtain), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Rèm phòng ngủ

Với Rèm phòng ngủ (curtain), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Rèm phòng ngủ (curtain) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 006e492cadc1196f8b09809e27a73d6ed80b8dfe4ae6bfeeb7bbab61d04cdec5.
