# PLAN - Activity Visibility by Faculty and University

## 🔴 Phase -1: Context Check

**Goal**: Hiển thị activities theo Tổ chức (Trường, Khoa) dựa trên hồ sơ sinh viên.
**Current State**:

- Có model `Organization` hỗ trợ cây đệ quy (`Đoàn trường`, `Đoàn khoa`, `Chi đoàn`, `Câu lạc bộ`).
- Có model `OrganizationMember` liên kết `User` với `Organization`.
- Model `Activity` có thuộc tính `organization` là khóa ngoại trỏ tới `Organization`.

## 🟡 Phase 0: Socratic Gate (Resolved)

- **Q1: Cơ chế xác định Tổ chức của Sinh viên**: Sếp đã chốt làm cách chuẩn là viết tính năng **Import sinh viên từ Excel**. Hệ thống khi nhận data từ Excel sẽ tự động tạo `User`, tạo `StudentProfile` và TỰ ĐỘNG GÁN sinh viên đó làm `OrganizationMember` của các `Organization` tương ứng (Khoa, Lớp).
- **Q2: Phạm vi hiển thị**: Sếp đã chốt làm bao quát toàn bộ. Tức là sinh viên sẽ thấy:
  - Activities của Trường (toàn trường).
  - Activities của Khoa mà Sinh viên trực thuộc.
  - Activities của Lớp (Chi đoàn) mà Sinh viên trực thuộc.
  - Activities của các Câu lạc bộ mà Sinh viên tham gia.

## 🟢 Phase 1: Task Breakdown

**1. Tooling - Thêm Import Data Sinh Viên (Hàng loạt)**

- Sẽ tạo view import Excel cho việc tạo User hàng loạt. Lấy thông tin Tên, MSSV, Khoa, Lớp...
- Quét/tạo Organization tương ứng cho Khoa, Lớp nếu chưa có. Gán User đó thành `OrganizationMember`.

**2. Cập nhật Model (nếu cần thiết cho Helper)**

- Cập nhật hàm lấy cây id (Organization tree) của user nhanh nhất. Vì Model `Organization` có `parent_id` nhưng lấy lên xuống hơi thủ công, có thể viết thêm 1 property lấy tất cả ID của cha ông (tới cấp Đoàn Khoa/Trường).

**3. Cập nhật Activity Views (`StudentActivityListView`)**

- Tìm tổ chức cấp `Đoàn trường` (OrgType.UNION_SCHOOL). Lấy ID.
- Lấy list `organization_id` từ `OrganizationMember` mà sinh viên đang tham gia.
- Rewrite hàm `get_queryset()` của View danh sách Activity cho sinh viên:
  - `Activity.objects.filter(status='APPROVED')` AND
  - `(organization_id = TRUONG_ID OR organization_id IN user_org_ids_plus_parents)`.

## 🔵 Phase 2: Agent Assignments

- **Antigravity (Backend Developer)**: Code API/View Import Excel, Logic Backend cho `StudentActivityListView`.
- **Antigravity (Frontend Developer)**: Làm giao diện chọn file Import `admin/import_students.html` hoặc tương tự.
- **User (Người phê duyệt)**: Test và Verification theo Phase 3.

## 🟣 Phase 3: Verification Checklist

- [ ] Truy cập Admin/Staff role, import sinh viên file Excel (Mock data có khoa CNTT, Kinh Tế).
- [ ] Đăng nhập user Sinh viên Khoa CNTT, check xem có thấy Activity của Khoa Kinh Tế không (mong muốn là không).
- [ ] Check xem Activity cấp Trường có vào Dashboard của tất cả mọi người không.
- [ ] Check xem tham gia CLB IT (là member) có thấy Activity của CLB IT không.
