# Hướng dẫn mô phỏng: Quạt hút bếp

Quạt hút bếp (fan-kitchen) nằm tại Bếp, nhóm Quạt trong HomeMate. Tài liệu được sinh từ cấu hình controls của ứng dụng, không phải manual nhà sản xuất. Chưa có hãng/model, thông số phần cứng hay mã lỗi thực tế được xác minh.

## Các chức năng của Quạt hút bếp

Quạt hút bếp (fan-kitchen): Nút quạt [speed] hỗ trợ các mức rời rạc: 0 = Tắt; 1 = 1; 2 = 2; 3 = 3.

Quạt hút bếp (fan-kitchen): mức speed=0 là tắt. Lệnh bật quạt được ánh xạ tới mức dương thấp nhất được hỗ trợ; lệnh tắt về mức 0. Muốn tốc độ cụ thể, chọn đúng một mức đã liệt kê, không dùng giá trị trung gian.

Quạt hút bếp (fan-kitchen) có những mức điều khiển nào? Các mức tốc độ quạt được hỗ trợ là 0, 1, 2, 3. Mức 0 tắt quạt; các mức 1, 2, 3 bật quạt với tốc độ tương ứng. Đây là mức của đúng thiết bị Quạt hút bếp, không phải số mức của quạt ở phòng khác.

## Cách thao tác với Quạt hút bếp

Với Quạt hút bếp (fan-kitchen), mở danh sách Thiết bị, chọn đúng tên và dùng các control đã liệt kê. Nếu control yêu cầu nguồn bật, hãy bật thiết bị trước khi chỉnh trực tiếp.

Khi gửi yêu cầu cho trợ lý về Quạt hút bếp (fan-kitchen), nêu rõ tên/phòng và giá trị muốn đặt. Agent tạo đề xuất, chưa thực thi cho đến khi người dùng bấm Xác nhận. Có thể Từ chối nếu sai thiết bị hoặc sai giá trị. Đề xuất hết hạn thì gửi yêu cầu mới.

## Xử lý yêu cầu không được hỗ trợ cho Quạt hút bếp

Với Quạt hút bếp (fan-kitchen), nếu giá trị ngoài giới hạn hoặc chức năng không nằm trong controls, không cố dùng tham số của thiết bị khác. Kiểm tra lại dữ liệu backend và điều kiện nguồn; nếu cấu hình đã đổi, tài liệu này cần được sinh/nạp lại. Mã lỗi, tháo lắp, vệ sinh phần cứng và lịch bảo trì nhà sản xuất chưa có trong tài liệu mô phỏng này.

Tài liệu Quạt hút bếp (fan-kitchen) không lưu trạng thái đang bật/tắt, nhiệt độ đang đặt, vị trí hiện tại hoặc điện năng hôm nay. Các thông tin thay đổi theo thời gian phải tra cứu qua backend tools.

Nguồn biên soạn: snapshot backend HomeMate (tên, phòng, loại, controls) và quy tắc điều khiển trong mã nguồn ứng dụng. Mã cấu hình: a1b8fcd812ca4e116e908cf1b2cb64c1cd682c3013e27715a4aecd7527f3ed99.
