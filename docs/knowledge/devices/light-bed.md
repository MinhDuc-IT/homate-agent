# Hướng dẫn mô phỏng: Đèn phòng ngủ

Đèn phòng ngủ (light-bed) nằm tại Phòng ngủ, nhóm Đèn trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Đèn phòng ngủ

Đèn phòng ngủ (light-bed): Nguồn [power] hỗ trợ bật/tắt nguồn.

Đèn phòng ngủ (light-bed) chỉ có bật/tắt nguồn, chưa có control chỉnh độ sáng. Không áp dụng hướng dẫn dimming của đèn khác cho thiết bị này.

## Cách thao tác với Đèn phòng ngủ

Với Đèn phòng ngủ (light-bed), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Đèn phòng ngủ (light-bed), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Đèn phòng ngủ

Với Đèn phòng ngủ (light-bed), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Đèn phòng ngủ (light-bed) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: eadd045746a1c1fe3a95e0ad90ecbd6bbdde5f48d2383da8bb93bc5f4818b75e.
