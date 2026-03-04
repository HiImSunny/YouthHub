# PLAN-max-participants

## Goal Description

Thêm tính năng giới hạn số lượng sinh viên đăng ký tham gia (max participants) cho một hoạt động (Activity).
Hiện tại, UI của trang `detail.html` hiển thị placeholder `{{ activity.max_participants|default:"∞" }} NGƯỜI TỐI ĐA` nhưng model `Activity` chưa có field này và logic giới hạn đăng ký chưa được thực hiện.
Việc thêm field này sẽ giúp ban tổ chức kiểm soát được số lượng sinh viên tham gia, tránh tình trạng quá tải.

## User Review Required

- Giá trị mặc định khi tạo activity không điền `max_participants` là gì? (0 = không giới hạn, hay bỏ trống/NULL = không giới hạn?) -> Kiến nghị sử dụng `null=True, blank=True` để biểu thị không giới hạn (vô cực).

## Proposed Changes

### Database Models

#### [MODIFY] activities/models.py

- Thêm trường `max_participants` vào class `Activity`:
  `max_participants = models.PositiveIntegerField(null=True, blank=True, help_text="Giới hạn số lượng sinh viên đăng ký. Để trống nếu không giới hạn.")`
- Generate và apply migration (`python manage.py makemigrations` và `python manage.py migrate`).

### Backend Logic

#### [MODIFY] activities/views.py

- Cập nhật view `activity_create`: Xử lý thêm tham số `max_participants` từ POST request và lưu vào instance.
- Cập nhật view `activity_edit`: Xử lý thêm tham số `max_participants` từ POST request và cập nhật instance.
- Cập nhật view `activity_register`: Thêm logic kiểm tra (validation): Nếu `activity.max_participants` có giá trị và số lượng đăng ký hiện tại (status = 'REGISTERED') đã đạt hoặc vượt ngưỡng này, thì từ chối đăng ký và trả về lỗi bằng `messages.error()`.

### Frontend Templates

#### [MODIFY] templates/activities/form.html

- Thêm một input field dạng number cho phép nhập `max_participants` trong màn hình TẠO/SỬA hoạt động.
- Sắp xếp lại grid cho hợp lý.

## Verification Plan

### Automated Tests

- Hiện tại project chưa có hệ thống test unit/integration hoàn chỉnh (thiếu thư mục/file test rõ ràng theo tiêu chuẩn Django).

### Manual Verification

1. **Dựng/Migrate Database**: Chạy commands `makemigrations` và `migrate` không gặp lỗi.
2. **UI Tạo/Sửa Hoạt Động**:
   - Đăng nhập với tài khoản Staff/Admin.
   - Truy cập `/activities/create/`. Kiểm tra xem form có ô nhập "SỐ LƯỢNG NGƯỜI TỐI ĐA" không.
   - Nhập một số (ví dụ: 2) và tạo hoạt động.
   - Xem chi tiết hoạt động vừa tạo, đảm bảo UI hiển thị "2 NGƯỜI TỐI ĐA".
3. **Validation Đăng ký**:
   - Sử dụng 3 tài khoản Student khác nhau.
   - Sinh viên 1 đăng ký thành công.
   - Sinh viên 2 đăng ký thành công.
   - Sinh viên 3 đăng ký -> Báo lỗi "Hoạt động đã đủ số lượng đăng ký tối đa".
4. **Trường hợp Không giới hạn**:
   - Tạo hoạt động bỏ trống ô "SỐ LƯỢNG NGƯỜI TỐI ĐA".
   - Kiểm tra xem sinh viên có thể đăng ký bình thường không, hiển thị "∞ NGƯỜI TỐI ĐA" ở màn hình detail không.
