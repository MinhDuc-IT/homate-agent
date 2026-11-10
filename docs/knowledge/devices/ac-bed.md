# Hướng dẫn mô phỏng: Điều hòa phòng ngủ

Điều hòa phòng ngủ (ac-bed) nằm tại Phòng ngủ, nhóm Điều hòa trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Điều hòa phòng ngủ

Điều hòa phòng ngủ (ac-bed): Nguồn [power] hỗ trợ bật/tắt nguồn.

Điều hòa phòng ngủ (ac-bed): Nhiệt độ [temperature] hỗ trợ giá trị từ 16 đến 30 °C, bước 1. Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

Điều hòa phòng ngủ (ac-bed): Chế độ [mode] hỗ trợ chọn một trong: Làm lạnh (cool); Hút ẩm (dry); Quạt (fan). Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

Điều hòa phòng ngủ (ac-bed): chế độ cool được ứng dụng đặt nhãn Làm lạnh; dry là Hút ẩm; fan là Quạt. Đây là các lựa chọn chế độ trong mô phỏng, không phải xác nhận hiệu năng của điều hòa thực tế.

Điều hòa phòng ngủ (ac-bed) không có control thay đổi tốc độ quạt riêng. Chế độ fan (Quạt) trong mục Chế độ không đồng nghĩa có nút điều chỉnh tốc độ quạt.

## Cách thao tác với Điều hòa phòng ngủ

Với Điều hòa phòng ngủ (ac-bed), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp. Qua agent, điều chỉnh Nhiệt độ có thể kèm bật nguồn; cần kiểm tra nội dung đề xuất.

Khi gửi yêu cầu cho trợ lý về Điều hòa phòng ngủ (ac-bed), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Điều hòa phòng ngủ

Với Điều hòa phòng ngủ (ac-bed), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Điều hòa phòng ngủ (ac-bed) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 6dd2596a4be98d8a9441d39952a42952d06662ecc002563daa1268ef4c37913c.
