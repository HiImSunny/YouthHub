# PLAN: Phân tách Point Category theo Organization

## Thông tin chung

- **Yêu cầu:** Gắn `PointCategory` (Danh mục điểm rèn luyện) vào từng `Organization`. Xây dựng chức năng Thêm/Sửa/Xóa cho từng Organization và cho phép Hệ thống Admin (Superadmin) quản lý toàn bộ.
- **Mục tiêu:** Mỗi đơn vị/trường học có một hệ thống danh mục điểm riêng biệt. Đảm bảo tính bảo mật và đúng luồng nghiệp vụ.

---

## 🛑 Socratic Gate (Các câu hỏi cần làm rõ)

Hiển nhiên việc phân tách Point Category (Danh mục điểm) này là bắt buộc để các trường không bị ảnh hưởng lẫn nhau. Tuy nhiên, trước khi bắt tay làm (bằng lệnh `/create`), mình có 2 vấn đề cần bạn duyệt lại:

1. **Hierarchy (Phân cấp hiển thị):** Giả sử Trường "ĐH Khoa Học Tự Nhiên" tạo các mục điểm rèn luyện (VD: Hoạt động Thể thao, Hoạt động Tình nguyện). Các Khoa trực thuộc (VD: Khoa CNTT, chi đoàn lớp) có được phép thấy và sử dụng các Mục Điểm này không? Hay Khoa CNTT phải tự tạo loại điểm của riêng Khoa? (Thường thì cấp Trường tạo và các cấp con được dùng chung, bạn có muốn thiết kế kiểu này không?)
2. **Migration Data:** Bảng danh mục điểm hiện có dữ liệu cũ chưa? Nếu chưa có gì quan trọng, mình sẽ "xóa sạch" và cấu hình database mới mẻ hoàn toàn với khóa ngoại `<Organization>`. Tránh lỗi dữ liệu cũ. Hoặc mình có thể tạo lệnh gán ngẫu nhiên vào dữ liệu mặc định.

---

## Phân rã công việc (Task Breakdown)

### Phase 1: Cập nhật Models & Ràng buộc Database

- **Model:** `activities/models.py`.
- **Nhiệm vụ:**
  - Thêm khóa ngoại `organization` liên kết tới `core.Organization`.
  - Đổi unique của cột `code` thành `UniqueConstraint` kết hợp giữa `organization` và `code` (nghĩa là 2 tổ chức khác nhau có thể có 2 mã `CTXH` trùng nhau, nhưng trong 1 tổ chức không được trùng).
  - Khởi tạo migration và áp dụng thay đổi vào Database (chạy `makemigrations`, `migrate`).

### Phase 2: Logic Quản lý (View, Url, Forms)

- **Model:** `activities/views.py` (hoặc `core`), `activities/forms.py`, `urls.py`.
- **Nhiệm vụ:**
  - Tạo `PointCategoryForm`.
  - Tạo các view CRUD (`point_categories`, `point_category_create`, `point_category_update`, `point_category_delete`).
  - **Phân quyền Backend:** Cấp độ Staff chỉ được thao tác trên danh mục điểm của `Organization` mình (và có thể là cấp con nếu cần). Cấp độ Superadmin có quyền quản lý toàn cục.

### Phase 3: Xây dựng Giao diện

- **Model:** File HTML Templates.
- **Nhiệm vụ:**
  - Thêm chức năng **Quản lý Danh mục Điểm** lên Sidebar của Admin/Staff Dashboard.
  - Xây dựng bảng danh sách Point Category (Dùng Tailwind, có tính năng search/filter nếu là Admin tổng).
  - Form thêm / sửa (Sử dụng modal hoặc trang riêng biệt).
  - Xử lý UX/UI: nếu Điểm đó đã được một Hoạt động (Activity) dùng rồi, thì không cho phép Xóa mà chỉ chuyển `is_active = False` để tránh mất dữ liệu quá khứ.

---

## Tiêu chí Nghiệm thu (Verification Checklist)

- [ ] Database cấu trúc thành công ràng buộc `UniqueConstraint(organization, code)`.
- [ ] Tạo được 2 mã danh mục điểm giống nhau ở 2 Trường (Tổ chức) khác nhau.
- [ ] Dữ liệu hiển thị đúng trên Dashboard theo Organization của Staff đang đăng nhập.
- [ ] Menu điều hướng và các chức năng Thêm/Sửa/Xóa hoạt động trơn tru.
- [ ] Point Category khi tạo mới tự động gán Organization của người tạo nếu là Staff.
