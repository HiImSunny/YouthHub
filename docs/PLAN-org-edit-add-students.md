# PLAN - Edit/Delete Org & Quản lý Thành viên

## 🔴 Phase -1: Context Check

**Goal**:

1. Bổ sung tính năng Sửa / Xóa cho Tổ chức (Organization). Khi xóa thì tự động xóa hết các Tổ chức con của nó.
2. Đổi trang "Nhân sự" thành "Thành viên", chia làm 2 danh sách rõ rệt: Cán bộ (Staff/Officer) và Đoàn viên/Hội viên (Sinh viên thường).
3. Thêm tính năng "Thêm sinh viên" vào Tổ chức bằng cách gõ trực tiếp MSSV (chống lag).
4. Dời box "Import SV" vào trong trang Quản lý thành viên của từng Tổ chức, và tính năng Import lúc này sẽ **áp dụng CỨNG** cho chính Tổ chức đang đứng (bất kể là Đoàn trường, Khoa, Lớp hay Câu lạc bộ). Cột Khoa/Lớp trong file Excel mẫu sẽ không còn ý nghĩa tạo mới cấu trúc nữa, mà mọi người trong file đều bị "nhét" vào Tổ chức hiện tại.

## 🟡 Phase 0: Socratic Gate (Đã chốt)

Sếp đã quyết định:

- **Câu 1**: Cho phép xóa và xóa luôn tất cả children.
- **Câu 2**: Việc "Add sinh viên" thủ công sẽ dùng input MSSV như đề xuất.
- **Câu 3**: Box Import nằm ở org nào thì import thẳng vào org đó, áp dụng cho cả chi đoàn, clb, đoàn khoa, đoàn trường.
- **Bổ sung**: Không dùng chữ "Nhân sự", đổi thành "Thành viên" (bao gồm staff và sinh viên). Trong trang thiết kế chia thành 2 bảng rõ rệt.

## 🟢 Phase 1: Task Breakdown

**1. Thêm View / Giao diện Edit, Delete Org (`core/views.py`)**

- View `organization_edit(request, org_pk)`: Update tên, loại, parent.
- View `organization_delete(request, org_pk)`: Vì `Organization.parent` sử dụng `on_delete=models.CASCADE` (nên Django sẽ tự động xóa hết các ổ chức con cháu khi Tổ chức cha bị xóa). Chỉ cần verify `can_manage_org_staff(user, org)` và gọi `org.delete()`.
- Thêm nút **Sửa / Xóa** vào thẻ Card (`_org_card.html`) và Cây (`_org_tree_node.html`).

**2. Refactor Danh sách Thành viên (`org_staff.html` -> `org_members.html`)**

- Đổi các text HTML: "NHÂN SỰ" -> "THÀNH VIÊN".
- Trong view `org_staff_view` (có thể đổi tên hoặc giữ nguyên hàm nhưng template đổi): Tách danh sách `members` thành 2 queryset:
  - `officers`: `OrganizationMember` có `is_officer=True`.
  - `regular_members`: `OrganizationMember` có `is_officer=False`.
- Giao diện: Chia thành 2 khu vực (Table Cán bộ / Table Đoàn viên-Hội viên).

**3. Thêm chức năng "Add Sinh viên" (Gõ MSSV)**

- Giao diện: Tạo một Box "THÊM THÀNH VIÊN" có 1 ô `input type="text" name="student_code"`.
- View: Xử lý `action == 'add_student'`. Tìm `StudentProfile.objects.filter(student_code=...)`. Lấy ra User. Gán vào `OrganizationMember` với `is_officer=False, position='Thành viên'`. (Báo lỗi nếu không tồn tại MSSV).

**4. Dời Box "Import Sinh Viên" & Ép Org Context (`core/views.py`)**

- Trong trang Thành viên của Org, thêm Button "IMPORT TỪ EXCEL".
- Khi Submit Form Excel, gọi POST về một View mới (hoặc viết đè view cũ) là `import_members_to_org(request, org_pk)`.
- View `import_members_to_org`:
  - Lấy file Excel, quét dòng. Kiểm tra User tồn tại chưa (qua MSSV/Email).
  - Nếu chưa: Tạo User + Profile (Role: STUDENT). Nếu cột D, E trong file có cũng có thể kệ nó, chủ yếu là...
  - **Quan trọng nhất**: Gán ngay User đó vào cái Tổ chức `org_pk` (OrganizationMember, `is_officer=False`). Bỏ qua hết các logic tự đi tìm Đoàn Khoa/Lớp rườm rà của phiên bản cũ.

## 🔵 Phase 2: Agent Assignments

- **Antigravity**: Xây dựng backend + chỉnh sửa giao diện.
- **User (Sếp)**: Xem xét plan cập nhật, check lại và báo hiệu chạy `/[create] phase 1`.

## 🟣 Phase 3: Verification Checklist

- [ ] Admin có thể Sửa/Xóa. Xóa Khoa thì tất cả Lớp thuộc Khoa tự động bị xóa theo.
- [ ] Vào trang Thành viên của 1 Lớp, hiển thị 2 cục rõ ràng: Cán Bộ & Sinh Viên.
- [ ] Nhập MSSV vào ô Tìm kiếm rồi Thêm -> User xuất hiện ở danh sách Sinh Viên nhánh đó.
- [ ] Import Excel lúc đang đứng ở trang thành viên "CLB Tiếng Anh" -> Mọi sinh viên trong file tự động thành viên và thêm vào CLB Tiếng Anh (không ảnh hưởng tới Khoa).
