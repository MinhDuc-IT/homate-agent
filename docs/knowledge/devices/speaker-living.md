# Hướng dẫn mô phỏng: Loa phòng khách

Loa phòng khách (speaker-living) nằm tại Phòng khách, nhóm Loa trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Loa phòng khách

Loa phòng khách (speaker-living): Nguồn [power] hỗ trợ bật/tắt nguồn.

Loa phòng khách (speaker-living): Âm lượng [volume] hỗ trợ giá trị từ 0 đến 100 %. Khi thao tác trực tiếp trên giao diện, cần thỏa điều kiện power=true.

## Cách thao tác với Loa phòng khách

Với Loa phòng khách (speaker-living), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp. Qua agent, điều chỉnh Âm lượng có thể kèm bật nguồn; cần kiểm tra nội dung đề xuất.

Khi gửi yêu cầu cho trợ lý về Loa phòng khách (speaker-living), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Loa phòng khách

Với Loa phòng khách (speaker-living), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Loa phòng khách (speaker-living) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: c0ed213c33b2f0dff7465fd6a408419f195b5716bd4695327ed99a4db94e243f.
