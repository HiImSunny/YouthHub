# PLAN: Cập nhật Neo Brutalism cho trang Check-in và tinh chỉnh Logic thời gian điểm danh

## Context & Objectives

- **Vấn đề**:
  1. Trang quét mã điểm danh (`/attendance/checkin/xxx/`) vẫn còn giao diện cũ (Soft UI Gradient), chưa đồng bộ với phong cách Neo Brutalism hiện tại của hệ thống.
  2. Các mốc thời gian hiển thị trong file template đa phần chỉ có giờ (`H:i`) mà thiếu ngày tháng, gây bối rối không rõ là phiên của ngày nào.
  3. Logic phiên đang mở hiện tại chỉ dựa vào trạng thái (`status == 'OPEN'`), dẫn đến việc QR code full màn hình luôn hiện "PHIÊN ĐANG MỞ" dù chưa tới giờ điểm danh hoặc đã lố giờ tắt. Tương tự với trang checkin.
- **Mục tiêu**:
  - Gắn chặt thời gian thực vào các trạng thái điểm danh: `CHƯA BẮT ĐẦU`, `ĐANG DIỄN RA`, `ĐÃ KẾT THÚC`.
  - Hiển thị rõ ràng ngày tháng năm `d/m/Y` kết hợp cung giờ.
  - Redesign toàn bộ trang check-in bằng `Tailwind Neo Brutalism`.

---

## Task Breakdown

### Phase 1: Bổ sung Context Logic (Backend)

- **Mục tiêu**: Thêm biến nhận diện trạng thái thời gian thực. Bổ sung chặt chẽ điều kiện thời gian khi người dùng bấm xác nhận điểm danh.
- **Files**:
  - `attendance/views.py`:
    - Truyền thêm biến `now = timezone.now()` vào context của các hàm: `session_qr`, `session_detail` và `checkin_view`.
    - Trong hàm `checkin_submit`: Chặn đứng hành vi điểm danh nếu `now < session.start_time` (báo lỗi: Chưa tới giờ) hoặc `now > session.end_time` (báo lỗi: Phiên đã hết hạn).

### Phase 2: Render trạng thái thời gian cho trang QR Fullscreen

- **Mục tiêu**: Hiển thị chính xác trạng thái dựa vào mốc thời gian ở trang `/attendance/1/qr/`.
- **Files**:
  - `templates/attendance/qr_display.html`:
    - Dùng câu lệnh điều kiện `{% if now < session.start_time %}`, hiển thị CHƯA TỚI GIỜ ĐIỂM DANH (màu vàng/xám).
    - `{% elif now > session.end_time %}`, hiển thị ĐÃ KẾT THÚC ĐIỂM DANH (màu đỏ).
    - `{% else %}`, hiển thị PHIÊN ĐANG MỞ (màu xanh).
    - Sửa lại đoạn thời gian thành: `{{ session.start_time|date:"H:i d/m/Y" }} - {{ session.end_time|date:"H:i d/m/Y" }}`.

### Phase 3: Đồng bộ ngày tháng cho trang Session Detail

- **Mục tiêu**: Cập nhật định dạng ngày tháng tương tự cho trang chi tiết (`/attendance/1/`).
- **Files**:
  - `templates/attendance/session_detail.html`: Đổi các format `date:"H:i"` đi cùng ngày tháng để đỡ gây nhầm lẫn.

### Phase 4: Neo Brutalism trang Check-in (Mobile View)

- **Mục tiêu**: Lột xác trang `/attendance/checkin/xxx/` sang Brutalism, nơi sinh viên sẽ thấy sau khi quét QR bằng điện thoại.
- **Files**:
  - `templates/attendance/checkin.html` (và `checkin_closed.html` nếu cần gom lại):
    - Đổi thành nền trắng có chấm bi hạt.
    - Cấu trúc: Các khối Container bọc viền đen đậm dày `border-4 border-black`, đổ bóng `shadow-[4px_4px_0_0_#000]`. Buttons có màu sặc sỡ (`primary`, `accent-yellow`).
    - Thêm các khối báo lỗi tương tự Phase 2 nếu `now < start_time` (Chưa mở) hoặc `now > end_time` (Đã đóng). Người dùng không thể thấy form submit nếu nằm ngài khung giờ được cấp.

---

## Verification Checklist

- [ ] Truy cập trang QR trước mốc bắt đầu phải báo "Chưa tới giờ".
- [ ] Bấm vào Checkin trước mốc bắt đầu sẽ bị chặn với giao diện UI Brutalism đẹp mắt ngầu lòi, không render form xác nhận điểm danh.
- [ ] Các giờ giấc hệ thống đã có đầy đủ format kèm cả ngày và tháng (Ví dụ: 23:18 05/03/2026).
- [ ] Không thể bypass được backend để hack submit attendance khi lố hoặc chưa tới giờ (Backend Validation chặn lại).

---

## Agent Assignments

- **Antigravity Orchestrator**: Trực tiếp sửa Backend Python & UI Tailwind CSS qua từng Phase tuần tự. Thẩm định qua trình Auto Preview nếu cần.
