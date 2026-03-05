# PLAN: Cập nhật luồng Điểm rèn luyện (Attendance Points)

## 1. Context & Objective

- **Sự cố / Bất cập hiện tại**:
  1. Trang danh sách Phiên điểm danh (`/attendance/`) có nút xem "ĐIỂM". View này vốn dĩ là bảng điểm cá nhân, nên việc Admin/Staff thấy nút này là thừa thãi. Nút này cần bị ẩn đi với Admin & Staff, chỉ để dành cho Sinh viên truy cập.
  2. Tại trang "ĐIỂM RÈN LUYỆN" (`attendance/points.html`), phần hướng dẫn thông tin ghi cứng là `MỖI ĐIỂM DANH ĐƯỢC XÁC NHẬN = +5 ĐIỂM`. Đây là thông tin sai lệch vì số điểm được cộng phụ thuộc vào từng hoạt động cấu hình khác nhau, chứ không cố định ở mức 5.
  3. Giao diện Sidebar (`base.html`) ở chế độ sinh viên hoàn toàn thiếu mục truy cập vào chức năng Điểm rèn luyện, khiến Sinh viên rất khó thao tác nếu không biết đường dẫn.

- **Mục tiêu thay đổi**: Khắc phục cả 3 vấn đề trên nhằm làm trong sáng UX, điều hướng đúng phân quyền, và cung cấp thông tin chuẩn xác.

## 2. Phân tích hiện trạng & Task Breakdown

### Phase 1: Ẩn nút chức năng theo phân quyền

- **File cần sửa**: `templates/attendance/sessions.html`
- **Công việc**: Tìm block `header_actions`. Bao bọc thẻ liên kết `<a href="{% url 'attendance:points' %}">...ĐIỂM</a>` bằng điều kiện `{% if user.role == 'STUDENT' %}`. Điều này giúp nút Điểm trên góc phải chỉ hiện đúng cho sinh viên.

### Phase 2: Cập nhật thông báo trang Điểm

- **File cần sửa**: `templates/attendance/points.html`
- **Công việc**: Tìm dòng cứng mã: `MỖI ĐIỂM DANH ĐƯỢC XÁC NHẬN = +5 ĐIỂM`. Thay thế dòng text này thành một câu chuẩn xác mang tính khái quát, ví dụ: `ĐIỂM ĐƯỢC CỘNG TƯƠNG ỨNG THEO QUY ĐỊNH CỦA TỪNG HOẠT ĐỘNG` hoặc `SỐ ĐIỂM TUỲ THUỘC VÀO QUY ĐỊNH CỦA TỪNG HOẠT ĐỘNG`.

### Phase 3: Thêm Menu Điều hướng cho Sinh viên

- **File cần sửa**: `templates/base.html`
- **Công việc**: Định vị khu vực Sidebar dành cho sinh viên (`<!-- ═══ STUDENT NAV ═══ -->`). Bổ sung thêm một thẻ Link chuyển hướng tới thư mục chứa điểm Rèn luyện.
  - Text: `ĐIỂM RÈN LUYỆN`
  - Icon: `star`
  - URL: `{% url 'attendance:points' %}`
  - Logic xác định state active: `{% if 'points' in request.path %}`.

## 3. Verification Checklist

- [ ] Truy cập portal (/attendance/) bằng Admin/Staff: Xác minh KHÔNG còn hiện nút ĐIỂM ở Navbar thao tác.
- [ ] Truy cập portal (/attendance/) bằng Student: Nút ĐIỂM vẫn hiển thị.
- [ ] Truy cập vào trang xem Điểm (`/attendance/points/`): Không còn dòng chữ Fix cứng `+5 ĐIỂM`.
- [ ] Sidebar sinh viên (cột bên trái) phải xuất hiện Tab "ĐIỂM RÈN LUYỆN" hoạt động tốt và có logic hover/active đúng màu.

---
**Agent Assignments**: Giao lại cho Antigravity Orchestrator (Backend/Frontend Agent) triển khai code.
