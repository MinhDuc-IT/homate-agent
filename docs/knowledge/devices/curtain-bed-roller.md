# Hướng dẫn mô phỏng: Rèm cuốn phòng ngủ

Rèm cuốn phòng ngủ (curtain-bed-roller) nằm tại Phòng ngủ, nhóm Rèm trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Rèm cuốn phòng ngủ

Rèm cuốn phòng ngủ (curtain-bed-roller): Mức mở [preset] hỗ trợ chọn một trong: Đóng (closed); Mở hé (ajar); Mở hết (open).

Rèm cuốn phòng ngủ (curtain-bed-roller): Vị trí [position] hỗ trợ giá trị từ 0 đến 100 %.

Rèm cuốn phòng ngủ (curtain-bed-roller): position=0% là đóng, position=100% là mở hết; vị trí ở giữa tương ứng mở hé. Dùng phần trăm vị trí để chỉ định mức mở cụ thể; không suy ra thời gian chạy motor hoặc kích thước rèm từ giá trị này.

## Cách thao tác với Rèm cuốn phòng ngủ

Với Rèm cuốn phòng ngủ (curtain-bed-roller), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Rèm cuốn phòng ngủ (curtain-bed-roller), nêu rõ tên/phòng và giá trị muốn đặt. Thao tác thông thường có thể thực hiện ngay khi yêu cầu đã rõ và hợp lệ. Với thao tác cần xác nhận hoặc có xung đột, kiểm tra đề xuất trước khi đồng ý; có thể từ chối nếu sai thiết bị hoặc giá trị. Nếu đề xuất hết hạn, hãy gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Rèm cuốn phòng ngủ

Với Rèm cuốn phòng ngủ (curtain-bed-roller), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Rèm cuốn phòng ngủ (curtain-bed-roller) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 84c3826675cff1da04bd205a10daf680b405b46911fd1ae7d991b068cc5516d9.
