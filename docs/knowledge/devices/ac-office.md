# Hướng dẫn mô phỏng: Điều hòa khu bàn máy tính

Điều hòa khu bàn máy tính tại Phòng khách (ac-office) nằm tại Phòng khách, nhóm Điều hòa trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Điều hòa khu bàn máy tính

Điều hòa khu bàn máy tính tại Phòng khách (ac-office): Nguồn [power] hỗ trợ bật/tắt nguồn.

Điều hòa khu bàn máy tính tại Phòng khách (ac-office): Nhiệt độ [temperature] hỗ trợ giá trị từ 16 đến 30 °C, bước 1. Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

Điều hòa khu bàn máy tính tại Phòng khách (ac-office): Chế độ [mode] hỗ trợ chọn một trong: Làm lạnh (cool); Hút ẩm (dry); Quạt (fan). Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

Điều hòa khu bàn máy tính tại Phòng khách (ac-office): chế độ cool được ứng dụng đặt nhãn Làm lạnh; dry là Hút ẩm; fan là Quạt. Đây là các lựa chọn chế độ trong mô phỏng, không phải xác nhận hiệu năng của điều hòa thực tế.

Điều hòa khu bàn máy tính tại Phòng khách (ac-office) không có control thay đổi tốc độ quạt riêng. Chế độ fan (Quạt) trong mục Chế độ không đồng nghĩa có nút điều chỉnh tốc độ quạt.

## Cách thao tác với Điều hòa khu bàn máy tính

Với Điều hòa khu bàn máy tính tại Phòng khách (ac-office), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp. Qua agent, điều chỉnh Nhiệt độ có thể kèm bật nguồn; cần kiểm tra nội dung đề xuất.

Khi gửi yêu cầu cho trợ lý về Điều hòa khu bàn máy tính tại Phòng khách (ac-office), nêu rõ tên/phòng và giá trị muốn đặt. Thao tác thông thường có thể thực hiện ngay khi yêu cầu đã rõ và hợp lệ. Với thao tác cần xác nhận hoặc có xung đột, kiểm tra đề xuất trước khi đồng ý; có thể từ chối nếu sai thiết bị hoặc giá trị. Nếu đề xuất hết hạn, hãy gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Điều hòa khu bàn máy tính

Với Điều hòa khu bàn máy tính tại Phòng khách (ac-office), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Điều hòa khu bàn máy tính tại Phòng khách (ac-office) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: a531a1b3edc00937572d362ea938523bc4dbb0949ff08baced79fd89690a583d.
