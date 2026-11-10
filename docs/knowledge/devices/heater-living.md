# Hướng dẫn mô phỏng: Máy sưởi phòng khách

Máy sưởi phòng khách (heater-living) nằm tại Phòng khách, nhóm Máy sưởi trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Máy sưởi phòng khách

Máy sưởi phòng khách (heater-living): Nguồn [power] hỗ trợ bật/tắt nguồn.

Máy sưởi phòng khách (heater-living): Nhiệt độ [temperature] hỗ trợ giá trị từ 16 đến 30 °C, bước 1. Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

## Cách thao tác với Máy sưởi phòng khách

Với Máy sưởi phòng khách (heater-living), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp. Qua agent, điều chỉnh Nhiệt độ có thể kèm bật nguồn; cần kiểm tra nội dung đề xuất.

Khi gửi yêu cầu cho trợ lý về Máy sưởi phòng khách (heater-living), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Máy sưởi phòng khách

Với Máy sưởi phòng khách (heater-living), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Máy sưởi phòng khách (heater-living) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: 278ef4715ce40e5814607a00f4b034edf89d29cc12bd0fb1fb32732b08f5ceea.
