# PLAN: Cập nhật Trạng Thái Phiên và Bổ Sung Sửa Phiên (Extend Session)

## Context & Objectives

- **Vấn đề**:
  1. Dù đã qua giờ kết thúc điểm danh, ở trang danh sách (`/attendance/`) phiên vẫn luôn báo nhãn là `Đang mở`. Có vẻ nó phụ thuộc vào Nút "Đóng Phiên" thủ công thay vì thời gian thực.
  2. Khi lỡ hết giờ điểm danh nhưng có sinh viên đến muộn cần thông cảm, Admin/Staff không có cách nào để "Mở thêm 10 phút" vì hoàn toàn thiếu nút **Chỉnh Sửa Phiên (Edit Session)**.
- **Mục tiêu**:
  - Tự động thay đổi trạng thái tag ở cả Dashboard và Trang Chi tiết thành đỏ và báo "ĐÃ KẾT THÚC" dựa vào thời gian thực tế, dù Admin chưa ấn nút đóng (tương tự như màn Hình Quét Lớn).
  - Viết thêm View & UI để thay đổi thông tin `AttendanceSession` bao gồm tên, giờ mở, giờ kết thúc (nghĩa là "Kéo dài thời gian điểm danh").

---

## Task Breakdown

### Phase 1: Thêm logic Thời gian thực vào Danh sách Phiên

- **Mục tiêu**: Tag trạng thái ở list hoạt động tự động. Tự chuyển thành Đã Đóng / Chưa Mở như bên trang Check-in.
- **Files**:
  - `attendance/views.py`: Ở `sessions_view` và `session_detail`, cần truyền biến `now = timezone.now()` qua context để template có dữ liệu so sánh.
  - `templates/attendance/sessions.html`: Render cái tag "ĐANG MỞ" dựa trên:
    - NẾU `session.status == 'CLOSED'` -> Báo "ĐÃ ĐÓNG (THỦ CÔNG)".
    - HOẶC NẾU `now > session.end_time` -> Báo "ĐÃ KẾT THÚC".
    - HOẶC NẾU `now < session.start_time` -> Báo "CHƯA MỞ".
    - CÒN LẠI: "ĐANG MỞ".

### Phase 2: Cấu Trúc View & Form "Chỉnh Sửa Phiên"

- **Mục tiêu**: Thêm khả năng gõ lại thời gian của phiên (Edit).
- **Files**:
  - `attendance/urls.py`: Thêm path `<int:pk>/edit/` trỏ tới `session_edit`.
  - `attendance/views.py`:
    - Viết hàm `session_edit` để load lại dữ liệu cũ, bao gồm `start_time` và `end_time`.
    - Handle Form POST để cập nhật lưu lại vào CSDL. Validate thời gian hợp lệ.
  - `templates/attendance/session_edit.html`:
    - Duplicate UI từ `session_create.html` nhưng đổ data (`value="..."`) của session cũ vào. Áp dụng Neo Brutalism cho đúng Concept hiện tại.

### Phase 3: Gắn nút Edit vào UI

- **Mục tiêu**: Cho Staff bấm vào sửa dễ dàng.
- **Files**:
  - `templates/attendance/session_detail.html`:
    - Thêm 1 nút "CHỈNH SỬA" màu Vàng (accent-yellow) ngay cạnh nút "ĐÓNG PHIÊN" / "CHI TIẾT".
  - `templates/attendance/sessions.html`:
    - Cũng có thể bổ sung 1 nút Icon Bút chì hoặc thêm vào Card để truy cập Edit nhanh.

---

## Verification Checklist

- [ ] Trang danh sách đã tự động báo `ĐÃ KẾT THÚC` nếu lỡ vọt qua giờ.
- [ ] Truy cập `[url]/edit/` để sửa lại thông tin, nới rộng giờ kết thúc thêm 15 phút.
- [ ] Màn hình quét ở Sảnh và link Check-in di động tự động sống lại ngay khi nới hạn `end_time` ở bước trước.

---

## Agent Assignments

- **Antigravity Agent**: Update `views.py` và `urls.py`. Cập nhật file templates bằng các tool code modifications (`multi_replace_file_content`, `write_to_file`).
