# PLAN: Sửa lỗi mã QR và thiết kế lại giao diện Fullscreen QR

## Context & Objectives

- **Vấn đề**:
  1. Trang chi tiết phiên điểm danh (`/attendance/1/`) đang bị lỗi hiển thị dấu ngoặc nhọn do xuống dòng trong code template: `{{ session.end_time|date:"H:i" }}`. Đồng thời, mã QR ở trang này chỉ hiển thị icon placeholder thay vì hình ảnh QR thực tế.
  2. Trang Fullscreen QR (`/attendance/1/qr/`) đang dùng thiết kế Soft UI với Gradient không đồng nhất với ngôn ngữ Neo Brutalism của toàn bộ dự án. Mã QR chưa đủ to. Lỗi tương tự ngắt dòng `{{ session.end_time... }}` cũng xảy ra.
- **Mục tiêu**:
  - Khắc phục lỗi hiển thị text thời gian ở cả 2 trang.
  - Render hình ảnh mã QR thực tế trong trang chi tiết phiên thay vì icon mờ.
  - Đập đi xây lại giao diện trang Fullscreen QR, áp dụng triệt để Neo Brutalism (Viền đen đậm, màu sắc sặc sỡ, đổ bóng cứng gắt). Làm cho mã QR to nhất có thể.

---

## Task Breakdown

### Phase 1: Sửa lỗi cú pháp Template

- **Mục tiêu**: Xoá các dấu enter/xuống dòng dư thừa nằm bên trong thẻ `{{ }}` của Django Template. Do auto-formatter của IDE đã bẻ dòng sai.
- **Files**:
  - `templates/attendance/session_detail.html`: Line 26-27 -> gom lại thành 1 dòng.
  - `templates/attendance/qr_display.html`: Line 84-85 -> gom lại thành 1 dòng.

### Phase 2: Đưa mã QR thật vào trang Session Detail

- **Mục tiêu**: Sinh mã QR và truyền vào context của view `session_detail`, sau đó thay đổi HTML để hiện ảnh.
- **Files**:
  - `attendance/views.py`: Tại hàm `session_detail`, gọi `_qr_base64(checkin_url)` để lấy chuỗi Base64 và truyền biến `'qr_data'` vào `context`.
  - `templates/attendance/session_detail.html`: Di chuyển ảnh QR thực (thẻ `<img>`) vào trong thay thế cho thẻ `<span class="material-symbols-outlined...">qr_code_2</span>`.

### Phase 3: Redesign lại trang Fullscreen QR (Neo Brutalism)

- **Mục tiêu**: Xóa toàn bộ CSS cũ (gradient, rounded-3xl) tại `qr_display.html`.
- **Thực thi**:
  - Chuyển template kế thừa `{% extends 'base.html' %}` (hoặc tự thiết lập Tailwind Brutalism gốc nếu muốn ẩn sidebar). Cần giữ giao diện tinh gọn nhất để chiếu lên máy chiếu. Tốt nhất là không kế thừa `base.html` để toàn màn hình, nhưng phải link đến Tailwind và CSS typography.
  - Giao diện: Nền màu nhấn rực rỡ (VD: Vàng hoặc Xanh ngọc).
  - Khối mã QR chiếm diện tích lớn nhất ở giữa: thẻ `<img>` cực to bọc trong khung viền đen `border-4 border-black shadow-[8px_8px_0px_rgba(0,0,0,1)]`.
  - Có hiện rõ: Tên phiên điểm danh, thời gian (`start_time` - `end_time`), Tên hoạt động và Link thủ công rõ ràng. Căn chỉnh bằng Flexbox.

---

## Verification Checklist

- [ ] Truy cập `/attendance/1/` không còn dòng chữ lòi ngoặc `{{ }}`.
- [ ] Truy cập `/attendance/1/` thấy hiện mã QR đen trắng thực sự chứ không phải icon.
- [ ] Nhấp mở trang QR Fullscreen: Giao diện cực cháy, viền đen dày, mảng sáng, chữ in đậm gắt gỏng neo-brutalism.
- [ ] Khung quét QR chiếm tỷ lệ lớn nhất trên màn hình nhưng vẫn đủ chữ chú thích.

---

## Agent Assignments

- **Antigravity Orchestrator**: Trực tiếp sửa cả Backend & Frontend cho 3 Phase này.
