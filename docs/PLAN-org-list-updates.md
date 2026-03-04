# Kế hoạch Triển khai: Cập nhật trang danh sách Tổ chức

## 1. Phân tích Yêu cầu (Context Check)

- **Vấn đề hiện tại**: Các tổ chức (bao gồm cả cha và con) đang được hiển thị dạng lưới ngang (`grid`), làm mất đi tính phân cấp. Tổ chức cha và tổ chức con cùng nằm ngang hàng trông không hợp lý.
- **Yêu cầu 1 (Staff)**: Staff chỉ được xem (view) danh sách các tổ chức mà họ đang là thành viên (thuộc về).
- **Yêu cầu 2 (Admin)**: Admin thấy toàn bộ tổ chức, nhưng phải hiển thị dưới dạng đồ thị/cây (Tree view) để hiện rõ cấu trúc tổ chức (Cha -> Con).
- **Yêu cầu 3 (Chung)**: Tính năng Search (Tìm kiếm theo tên/mã tổ chức) và Filter (Lọc theo Loại Tổ chức).

## 2. Các Bước Thực Hiện (Task Breakdown)

### Phase 1: Cập nhật Backend (Logic)

**File**: `core/views.py` -> `organizations_view(request)`

- **Search & Filter**:
  - Nhận tham số `q` (từ khóa tìm kiếm name/code) và `org_type` (loại tổ chức) từ `request.GET`.
  - Thực hiện `.filter()` dựa trên các tham số này (nếu có).
- **Phân tách Query theo Role**:
  - `request.user.role == 'STAFF'`: Lấy danh sách ID các org mà staff (user) đang tham gia (`OrganizationMember.objects.filter(user=request.user)`). Query `Organization` giới hạn trong danh sách này.
  - `request.user.role == 'ADMIN'`: Lấy tất cả `Organization`. Để hiển thị dạng Tree, viết hàm helper nhóm các org lại thành cây đệ quy (`nested dict` hoặc thêm thuộc tính `children_list` vào org object) và pass vào template.
  
*(Lưu ý: Nếu có Search/Filter, cây tổ chức của Admin chỉ hiển thị các tổ chức khớp kết quả tìm kiếm, hoặc hiển thị cây chứa kết quả đó tuỳ vào UX. Tốt nhất là kết hợp phẳng nếu đang search, và hiện cây nếu không search, hoặc luôn hiện cây nhưng bôi đậm).*

### Phase 2: Cập nhật Frontend (Giao diện)

**File**: `templates/core/organizations.html`

- **Thanh Tìm kiếm & Lọc (Search & Filter Bar)**:
  - Tạo tag `<form method="GET">` gồm input text, `<select>` Loại tổ chức, và nút submit.
- **Hiển thị cho Admin (Tree View)**:
  - Nếu `request.user.role == 'ADMIN'`: Hiển thị dạng danh sách lồng nhau (nested list, hoặc dùng flex-col với margin-left để thụt lề cho từng cấp độ: Đoàn trường -> Đoàn khoa -> Chi đoàn). Không dùng `grid-cols-3` chung chạ để tránh phá vỡ giao diện hệ thống cây.
- **Hiển thị cho Staff (List View)**:
  - Nếu `request.user.role == 'STAFF'`: Có thể giữ dạng Card (grid) như hiện tại vì dữ liệu đã được lọc chặt, rành mạch và chỉ có các org họ thuộc về.

### Phase 3: Kiểm thử & Xác nhận (Verification Checklist)

- [ ] Login Admin: Thấy đầy đủ cây tổ chức. Thấy thẻ thụt lề tương ứng quan hệ cha-con. Tìm kiếm và lọc hoạt động.
- [ ] Login Staff: Không thấy toàn bộ tổ chức, chỉ thấy tổ chức mình đã join. Tìm kiếm và lọc trong giới hạn tổ chức của mình.
- [ ] Mọi đường link (Quản lý nhân sự, Tạo tổ chức) vẫn giữ nguyên trạng thái đúng đối với role tương ứng.
