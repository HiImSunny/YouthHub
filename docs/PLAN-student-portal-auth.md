---
title: Kế hoạch phân quyền, Portal Sinh viên và Auth
description: Kế hoạch triển khai Dashboard sinh viên, Đăng ký/Đăng nhập, và Phân cấp quyền dựa trên models hiện tại (không đổi DB).
status: DRAFT
---

## KẾ HOẠCH TRIỂN KHAI YOUTHHUB: PORTAL SINH VIÊN & AUTHORIZATION

## 1. Yêu cầu từ người dùng

- **Student Portal:**
  - Sinh viên chỉ xem được hoạt động của Khoa/Trường và của Tổ chức (CLB) mình tham gia.
  - Fix status hoạt động trên trang của SV: Mất các label Nháp/Chờ duyệt, chuyển thành **Chuẩn bị diễn ra**, **Đang diễn ra**, **Đã kết thúc** dựa trên timeline.
  - Nút **Điểm danh**: Chỉ hiện khi thời gian hiện tại nằm trong khoảng thời gian của một `AttendanceSession`.
  - **Student Dashboard**: Hiển thị tổng điểm, tổng số lượt điểm danh, danh mục điểm. Kèm bảng danh sách các phiên đã điểm danh (hiện loại điểm, trạng thái Pending/Verified/Rejected).
- **Authentication & Account:**
  - Trang **Đăng ký (Register)**: Mặc định role `STUDENT`. Up lên `STAFF` phải liên hệ Admin.
  - Đăng nhập (Login): Hỗ trợ cả **Username** lẫn **Email**.
  - Đổi mật khẩu (Change Password) trong trang Profile.
- **Phân quyền (Hierarchy) - KHÔNG ĐỔI DATABASE:**
  - Ai được tạo activities, duyệt activities, tạo tổ chức, duyệt điểm danh, v.v. dựa trên `Organization`, `OrganizationMember`, `User.role`.
- **Quản lý Ngân sách (Budget Management):**
  - Xây dựng giao diện xem/thêm/sửa `Budgets` và `BudgetItems` cho các Hoạt động (Activity).
  - Phân quyền: Cán bộ Đoàn-Hội (Staff) tạo Dự trù kinh phí -> Admin phê duyệt.

---

## 2. Các câu hỏi làm rõ (Socratic Gate)

> **CẦN SẾP XÁC NHẬN:** Mọi logic phân quyền dưới đây được thiết kế để **không cần đổi Database**. Xin hãy kiểm tra xem logic này đúng ý chưa?

### 2.1. Logic phân quyền cấp bậc (Role Hierarchy)

Vì không đổi DB, chúng ta sẽ dựa vào Role và Organization Hierarchy:

1. **Admin (`role='ADMIN'`, `is_superuser=True`)**:
   - Toàn quyền: Tạo Org, sửa/xoá mọi Activity, xác nhận mọi Attendance Record.
   - Chỉ Admin mới có nút thay đổi User Role (từ Student -> Staff).
2. **Staff (`role='STAFF'`)**:
   - Từ `OrganizationMember` nơi `is_officer=True`:
   - **Tạo Hoạt động**: Chỉ được tạo hoạt động cho Tổ chức (Org) mà Staff đó đang làm Officer.
   - **Duyệt Điểm danh**: Được verify `AttendanceRecord` cho các hoạt động của Tổ chức mình quản lý.
   - **Duyệt Hoạt động (Approve Activity)**:
     - Cách 2: Staff của tổ chức **Cấp trên** (Parent Org) được duyệt hoạt động của tổ chức **Cấp dưới** (Child Org). Ví dụ Staff Đoàn Trường duyệt cho Đoàn Khoa.
     - *(Admin vẫn có quyền duyệt mọi hoạt động)*.
   - **Tạo Tổ chức (Create Org)**: Chỉ Admin mới có quyền tạo Tổ chức mới (để tránh spam).
   - **Quản lý Staff**: Staff của Parent Org có quyền gán/xoá Staff cho Child Org của mình.
3. **Student (`role='STUDENT'`)**:
   - Cấp quyền xem:
     - Hoạt động của Đoàn Trường (public).
     - Hoạt động của Tổ chức cha (Đoàn Khoa của sinh viên đó).
     - Hoạt động của Câu lạc bộ/Chi đoàn mà sinh viên là member.

*(Nếu Sếp đồng ý với logic trên, tôi sẽ tiến hành code dựa theo quy tắc này)*.

---

## 3. Các đầu việc cụ thể (Tasks)

### Phase A: Authentication & User Profile

- [ ] **A1:** Tạo view/template `register` (Tạo `User` với role STUDENT + tạo bản ghi `StudentProfile`).
- [ ] **A2:** Chỉnh sửa backend authentication để hàm Login chấp nhận đồng thời Username hoặc Email.
- [ ] **A3:** Thêm chức năng Đổi mật khẩu (`change_password`) trong trang User Profile.

### Phase B: Quyền Quản lý (Staff & Admin) - Backend Logic

- [ ] **B1:** Hàm tạo hoạt động -> Ràng buộc select Organization (Staff chỉ chọn được org mình quản lý).
- [ ] **B2:** Hàm phê duyệt hoạt động -> Lọc danh sách Chờ duyệt dựa trên Child Orgs (Cho Staff cấp trên) hoặc All (Cho Admin).
- [ ] **B3:** Quản lý Staff -> Thêm tính năng cho phép Parent Org Staff có thể thêm/xóa `OrganizationMember` (is_officer=True) cho Child Orgs của mình.
- [ ] **B4:** Quyền tạo Tổ chức -> Khoá chỉ dành cho Admin.

### Phase C: Portal Sinh viên (Student View)

- [ ] **C1:** Trang danh sách Hoạt động (`/activities/` đối với Student):
  - Lọc query: `Trường + Khoa + Các nhóm đã join`.
  - Override logic Status thành dạng Time-based: "Sắp diễn ra" (start_time > now), "Đang diễn ra", "Đã kết thúc".
- [ ] **C2:** Trạng thái đăng ký & Nút Điểm danh (Trên trang chi tiết Activity):
  - Kiểm tra xem hiện tại có `AttendanceSession` nào đang `OPEN` và trong giờ (start <= now <= end) hay không.
  - Nếu có, hiển thị nút "Điểm danh ngay" chuyển hướng tới form nhập Code/Chụp ảnh.
- [ ] **C3:** Student Dashboard (Trang cá nhân của sinh viên):
  - Tính tổng điểm Rèn luyện (dựa theo `ActivityPoint`).
  - Đếm tổng số buổi đã điểm danh hợp lệ.
  - Bảng Lịch sử Điểm danh: Join `AttendanceRecord` với `Activity` và `PointCategory`. Hiển thị Trạng thái duyệt.

### Phase D: Quản lý Ngân sách (Budget)

- [ ] **D1:** Tạo View & Form cho phần Budget (Hiển thị form liệt kê `danh sách Thu Chi` `budget_items` thuộc một `Budget` của Hoạt động).
- [ ] **D2:** Logic phê duyệt: Staff lập Dự trù Kinh phí (Status=DRAFT) -> Cấp trên hoặc ADMIN phê duyệt (APPROVED/REJECTED).
- [ ] **D3:** Tích hợp giao diện: Thêm tab "Ngân sách" vào trang chi tiết Activity (dành cho Staff/Admin).

---

## 4. Verification Plan (Test)

- Đăng ký một tài khoản mới -> Check xem tự động có StudentProfile không.
- Đăng nhập bằng email vừa đăng ký -> Check pass.
- Bằng tài khoản Student: Vào trang Activity, check xem filter lọc đúng Khoa/Trường/CLB chưa.
- Mở Admin để tạo Attendance Session trong khoảng thời gian hiện tại -> Thấy nút "Điểm danh" hiện trên giao diện SV.
- Xem Dashboard sinh viên hiển thị logic đúng hay sai.
