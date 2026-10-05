# Copy Unity WebGL build output vào đây (cùng cấp với README này):
#
#   public/unity/
#     index.html
#     Build/          ← *.data, *.framework.js, *.loader.js, *.wasm
#     TemplateData/   ← nếu Unity tạo kèm
#
# Sau đó chỉ cần `pnpm dev` — không cần python http.server.
# URL iframe: /unity/index.html  (xem VITE_UNITY_WEBGL_URL trong .env)
#
# Lưu ý: build với Compression Format = Disabled (hoặc Gzip + cấu hình server).
# File .br (Brotli) thường lỗi trên Vite/HTTP local.
#
# Embed tip: sau mỗi lần Unity Build lại, nhớ giữ chỉnh full-bleed
# (style.css nền #05080d, ẩn #unity-footer, canvas 100%) — Unity sẽ
# ghi đè index.html / TemplateData/style.css về template mặc định (nền trắng).
# Áp lại: body/#unity-canvas background #05080d, container inset 0,
# canvas width/height 100%, #unity-footer { display: none }.

Đặt nội dung WebGL build vào thư mục này.
