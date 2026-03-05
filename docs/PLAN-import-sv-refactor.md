# PLAN - Import Sinh Viên (Refactor cho STAFF)

## 🔴 Phase -1: Context Check

**Goal**: Cho phép cả Admin và Staff sử dụng tính năng "Import sinh viên từ Excel", giới hạn quyền import đúng tổ chức quản lý của Staff, và di chuyển menu "Import SV" vào khu vực thuận tiện hơn.
**Current State**:

- URL `/import-students/` được protect bởi `@admin_required`.
- Trong file `base.html`, menu "Import SV" nằm dưới phân hệ `ADMIN ONLY`.
- Khi import, view tự động lấy/tạo `UNION_FACULTY` từ cột `D: Khoa` và tạo user/profile.

## 🟡 Phase 0: Socratic Gate (User Clarification Needed)

Sếp cần chốt giúp em các vấn đề sau trước khi nhảy sang code:
**Câu hỏi số 1: Xử lý dữ liệu vi phạm quyền của Staff**

- Khoa (`UNION_FACULTY`) đang được nhận diện từ cột D.
- Nếu một **Staff của Khoa CNTT** dùng tài khoản họ để upload một file Excel chứa **Sinh viên của Khoa Kinh Tế**, hệ thống nên:
  - Báo lỗi dòng đó và bỏ qua? (Nghĩa là Staff Khoa CNTT vẫn import được những sinh viên CNTT nằm chung file với Khoa Kinh Tế, các dòng Khoa Kinh Tế sẽ báo đỏ không được tạo).
  - Hay **Hủy toàn bộ file** để đảm bảo tính toàn vẹn?
👉 *Đề xuất: Chặn luôn từ dòng và báo lỗi, những dòng hợp pháp vẫn tạo để không tốn công Staff sửa.*

**Câu hỏi số 2: Form Upload SV ở giữa**

- Sếp nói "cho phần form import sv ở giữa đi" -> Ý sếp là dời nút menu "Import SV" trong Sidebar lên phần dùng chung (nằm gần menu "Tổ chức") hay sếp muốn căn giữa css cái form upload ngay trên trang web?

## 🟢 Phase 1: Task Breakdown

**1. Sửa quyền truy cập - `core/views.py`**

- Đổi decorator của `import_students_view` và `download_import_template` từ `@admin_required` thành `@staff_required`.

**2. Ràng buộc quyền Import (Quy trình AuthZ)**

- Tại View, gọi `manageable_orgs = get_manageable_orgs(request.user)`.
- Nếu User là ADMIN: `is_unrestricted = True` (mặc định passthrough).
- Nếu User là STAFF: `is_unrestricted = False`.
- Khi lặp đọc từng dòng của file Excel, hệ thống tìm ra `faculty_org`.
- Nếu `is_unrestricted == False` và `faculty_org` đó **KHÔNG** nằm trong `manageable_orgs`:
  - Ghi vào list lỗi: *"Dòng X: Bạn không có quyền quản lý Khoa '...' (Chỉ dành cho cán bộ quản lý)."*

**3. Cập nhật Sidebar và Giao diện**

- Trong `base.html`: Cắt link `<a href="... import_students">` từ mục `ADMIN ONLY` lên nhóm `QUẢN TRỊ` dùng chung cho STAFF.
- Đưa form upload ra layout có content center (nếu sếp có ý đó).

## 🔵 Phase 2: Agent Assignments

- **Antigravity (Backend & FrontEnd)**: Code logic phân quyền và xử lý UI file base + file template.
- **User (Reviewer)**: Xem xét plan và xác nhận duyệt bằng `/[create] phase 1`.

## 🟣 Phase 3: Verification Checklist

- [ ] Login `admin`, test menu Import SV -> import file của Khoa CNTT.
- [ ] Logout, Login vào `staff_cnnt`.
- [ ] Đẩy file upload chứa Sinh viên khoa CNTT & Sinh viên khoa Kinh tế.
- [ ] Báo thành công Khoa CNTT & Hiển thị lỗi báo "Bạn không có quyền quản lý Khoa Kinh tế".
