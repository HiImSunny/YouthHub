# PLAN: Fix Alert Messages

## Context & Objectives

- **Người dùng yêu cầu**:
  1. Hầu hết các thông báo hệ thống (flash messages) hiện đang hiển thị dưới dạng tiếng Việt không dấu (VD: `Da dang xuat thanh cong`, `Xoa quyen can bo...`), gây mất thẩm mỹ và không chuyên nghiệp.
  2. Ở góc giao diện, người dùng không có cách nào để chủ động ấn tắt (dấu `x`) bảng thông báo đi mà cứ phải để nó nằm yên trên màn hình.
- **Mục tiêu**:
  - Dịch / Gắn dấu toàn bộ các nội dung thông báo hệ thống xuyên suốt project.
  - Cập nhật UI trong `base.html` để thêm nút **Đóng (Close)** cho từng dòng thông báo.

---

## Task Breakdown

### Phase 1: Thêm tương tác & Nút tắt cho khối Thông báo (Alert)

- **File cần sửa**: `templates/base.html` (Phần `# Messages` khoảng dòng 229).
- **Chi tiết thực thi**:
  - Đổi block chứa từng message (trong vòng lặp `{% for message in messages %}`) từ dạng div đơn thuần thành `display: flex; justify-between; items-center`.
  - Bọc phần nội dung text bằng `<span>{{ message }}</span>`.
  - Thêm `<button class="hover:opacity-75" onclick="this.parentElement.remove()"><span class="material-symbols-outlined text-lg">close</span></button>` sang góc phải.
  - *Kết quả*: Mọi thông báo đều có nút `X` ở góc, người dùng có thể nhấp để ẩn thông báo.

### Phase 2: Cập nhật nội dung thông báo sang Tiếng Việt chuẩn (Có dấu)

- **Phạm vi file**: Toàn bộ các file `views.py` xử lý logic:
  - `users/views.py` (vd: `Da dang xuat thanh cong` -> `Đã đăng xuất thành công`, `Sai ten dang nhap...` -> `Sai tên đăng nhập/email hoặc mật khẩu.`)
  - `core/views.py` (vd: `Da xoa quyen can bo khoi...` -> `Đã xoá quyền cán bộ khỏi...`)
  - `activities/views.py`
  - `attendance/views.py`
- **Chi tiết thực thi**:
  - Quét hệ thống tìm toàn bộ các method `messages.success()`, `messages.error()`, `messages.info()`, `messages.warning()`.
  - Thay thế chuỗi không dấu thành Tiếng Việt có dấu đầy đủ, chuẩn ngữ pháp.

---

## Verification Checklist

- [ ] Mở ứng dụng, tạo ra thông báo lỗi cơ bản (Thử đăng nhập sai mật khẩu). Khối thông báo phải có chữ ĐÚNG DẤU (`Sai tên đăng nhập/email hoặc mật khẩu.`) chứ không phải ghi không dấu nữa.
- [ ] Ở góc báo lỗi phải có nút *Close* (dấu X), nhấn vào nút này phải khiến khối thông báo lập tức biến mất (ẩn đi).
- [ ] Thử thực hiện lệnh Đăng xuất để xem popup thông báo cũng hiển thị tốt: `Đã đăng xuất thành công.`

---

## Agent Assignments

- **Antigravity Orchestrator (Fullstack)**: Xử lý thay đổi UI ở Frontend sau đó RegEx Replace đồng loạt tất cả file ở Backend.
