# Hướng dẫn mô phỏng: Đèn gương phòng tắm

Đèn gương phòng tắm (light-bath-mirror) nằm tại Phòng tắm, nhóm Đèn trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Đèn gương phòng tắm

Đèn gương phòng tắm (light-bath-mirror): Nguồn [power] hỗ trợ bật/tắt nguồn.

Đèn gương phòng tắm (light-bath-mirror) chỉ có bật/tắt nguồn, chưa có control chỉnh độ sáng. Không áp dụng hướng dẫn dimming của đèn khác cho thiết bị này.

## Cách thao tác với Đèn gương phòng tắm

Với Đèn gương phòng tắm (light-bath-mirror), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Đèn gương phòng tắm (light-bath-mirror), nêu rõ tên/phòng và giá trị muốn đặt. Thao tác thông thường có thể thực hiện ngay khi yêu cầu đã rõ và hợp lệ. Với thao tác cần xác nhận hoặc có xung đột, kiểm tra đề xuất trước khi đồng ý; có thể từ chối nếu sai thiết bị hoặc giá trị. Nếu đề xuất hết hạn, hãy gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Đèn gương phòng tắm

Với Đèn gương phòng tắm (light-bath-mirror), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Đèn gương phòng tắm (light-bath-mirror) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 94787d18e4ce8c47e8c3e90b4d894304a6ddb1aa56b37dfc027bbb3eb4dedb39.
