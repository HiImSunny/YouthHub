# PLAN: User Details & Student ID Display

## 1. Context & Objective

- **Mục tiêu**:
  1. Hiển thị mã số sinh viên (Student ID / `student_code`) bên cạnh thông tin người dùng (với những user là Sinh viên).
  2. Thêm tính năng "Xem chi tiết" (Detail View) cho mỗi người dùng tại trang Danh sách User tổng (`/users/`) và trang Thành viên Tổ chức (`org_staff.html`).
- **Lý do**: Hiện tại UI chỉ hiển thị email, gây khó khăn trong việc định danh sinh viên. Không có cách nào xem nhanh toàn bộ profile của một user (thông tin cá nhân, khoa/lớp, các tổ chức đang tham gia, etc).

## 2. Phân tích hiện trạng

- `users.models.User` có liên kết 1-1 với `StudentProfile` thông qua `user.student_profile`.
- `StudentProfile` chứa trường `student_code`.
- Dữ liệu ở view có thể được truy xuất thông qua `{{ member.user.student_profile.student_code }}` hoặc `{{ user.student_profile.student_code }}`.
- Cần tạo một endpoint/view mới (hoặc modal update) để hiển thị Modal chi tiết thành viên. Do UI mang phong cách Brutalism, một trang Detail riêng biệt hoặc một Modal to bản (Dialog) phù hợp với template. Sẽ ưu tiên thêm vào một trang Detail riêng `user_detail.html` hoặc một Modal Fragment load bằng HTMX/JS (Nếu code đang dùng cơ chế này, hoặc dùng Link sang trang chi tiết). Theo mô hình hiện tại, tạo một View `UserDetailView` và url `/users/<id>/` là cách sạch sẽ và dễ chia sẻ link nhất. Tuy nhiên, nếu user chỉ muốn xem nhanh dạn popup, có thể dùng Bootstrap/Tailwind Modal. Dựa trên code hiện tại không thấy nhắc đến framework Modal cụ thể nào ngoài các form submit cơ bản, dùng một trang `/users/<int:pk>/` hoặc modal HTML cơ bản.

## 3. Task Breakdown (Chi tiết công việc)

### Phase 1: Hiển thị Mã số Sinh viên trên UI

- **File cần sửa**:
  - `templates/core/org_staff.html`: Thêm mã số sinh viên vào danh sách thành viên (bên cạnh Email hoặc thay thế Email ở các dòng mô tả).
  - `templates/users/user_list.html` (Nếu có): Cập nhật tương tự.
- **Chi tiết thực thi**:
  - Dùng thẻ template: `{% if member.user.role == 'STUDENT' and member.user.student_profile %}{{ member.user.student_profile.student_code }} - {% endif %}`.

### Phase 2: Chức năng Xem chi tiết người dùng

- **Cách tiếp cận**: Tạo một trang User Detail chuyên biệt (`/users/<int:user_id>/`).
- **Backend (Views & URLs)**:
  - Thêm `user_detail` view trong `users/views.py` (hoặc view tương ứng quản lý user).
  - Cập nhật `users/urls.py` thêm path `path('<int:user_id>/', views.user_detail, name='user_detail')`.
- **Frontend (Templates)**:
  - Tạo file `templates/users/user_detail.html` với thiết kế Brutalism.
  - Nội dung bao gồm:
    - Thông tin cơ bản (Avatar avatar_url, Tên, Username, Email, Phone, Role, Status).
    - Thông tin sinh viên (Nếu role = STUDENT): MSSV, Khoa, Lớp, Khóa.
    - Tổ chức đang tham gia (Truy vấn từ `user.memberships.all()`).
  - Cập nhật các bảng danh sách ở `org_staff.html` và danh sách user: Thêm nút "XEM" hoặc biến tên user thành Link click được dẫn tới trang detail.

### Phase 3: Kiểm thử

- Đảm bảo MSSV hiển thị chính xác ở `org_staff.html`.
- Xác nhận trang Detail truy cập bình thường.
- Ngăn chặn lỗi khi truy cập Detail của Admin (không có `StudentProfile`).

## 4. Verification Checklist

- [ ] MSSV hiển thị đúng trên trang `/organizations/<id>/staff/` (hoặc thành viên).
- [ ] Click vào tên user / nút xem sẽ mở ra xem được chi tiết.
- [ ] Trang User Detail hiển thị đầy đủ thông tin (Hồ sơ sinh viên, các tổ chức đã tham gia).
- [ ] Giao diện Brutalism ăn khớp với theme hiện tại.
