# Kế Hoạch: Duyệt Điểm Danh & Cộng Điểm Hoạt Động (Activity Attendance & Points)

## 🎯 Mục Tiêu (Context Check)

- Cập nhật hệ thống để Hoạt động (`Activity`) có thể cấu hình **số điểm cộng** bên cạnh phân loại điểm.
- Cải tiến logic duyệt điểm danh: Sinh viên phải tham gia **đầy đủ tất cả các phiên điểm danh** của một hoạt động thì mới đủ điều kiện được duyệt và cộng điểm.
- Cải thiện giao diện duyệt điểm danh (cho Cán bộ/Admin): Gom nhóm các phiên điểm danh theo **Sinh viên + Hoạt động**, hiển thị trực quan (ví dụ: "Đã điểm danh 1/2 phiên", "Đã điểm danh 2/2 phiên") để dễ dàng đưa ra quyết định duyệt/từ chối toàn bộ cho sinh viên đó.
- Cấp quyền cộng điểm `ActivityPoint` tự động khi sinh viên được duyệt hoàn thành hoạt động.

## ❓ Socratic Gate (Các câu hỏi làm rõ - Ghi nhớ khi triển khai)

1. **Duyệt một phần?** **Quyết định:** Có thể duyệt cho những bạn điểm danh không đủ (1/2, 1/3 phiên) bù lại điểm cộng vẫn nhận Full dựa vào quyết định của Cán bộ duyệt. Hệ thống sẽ không cấm duyệt.
2. **Khi nào duyệt?** Cán bộ sẽ duyệt "Cấp điểm cho sinh viên này" (cấp Hoạt động), và hệ thống tự động update toàn bộ `AttendanceRecord` liên quan của sinh viên trong hoạt động đó thành `VERIFIED`, đồng thời sinh ra `ActivityPoint`.
3. **Hiển thị giao diện:** (Đã chọn) Sử dụng Table gom nhóm theo `Student`, liệt kê các cột là `Phiên 1`, `Phiên 2`... để Cán bộ tick chọn duyệt hoặc hệ thống tự highlight xanh những người đủ điều kiện. Dễ nhìn, tối ưu nhất cho người dùng.

## � Schema Review (Kết quả kiểm tra — 2026-03-04)

> Phát hiện sau khi review toàn bộ models trước khi bắt đầu Phase 1.

| # | Issue | Mức độ | Giải pháp |
|---|-------|--------|-----------|
| 1 | `Activity` thiếu field `points` | 🔴 Blocker | Thêm `DecimalField` vào `Activity` |
| 2 | `ActivityPoint` unique constraint include `reason` — dễ cộng trùng | 🔴 Blocker | Đổi thành `unique(student, activity)` |
| 3 | `AttendanceRecord.activity` FK thừa (redundant qua session) | 🟡 Medium | Xóa FK, truy cập qua `attendance_session__activity` |
| 4 | `ActivityPoint` thiếu FK `point_category` (snapshot) | 🟡 Medium | Thêm FK `point_category` |
| 5 | `ActivityPoint` thiếu `awarded_by` + `awarded_at` | 🟡 Medium | Thêm 2 field audit |
| 6 | `ActivityRegistration` thiếu status `ATTENDED`/`POINT_AWARDED` | 🟡 Medium | Thêm 2 giá trị vào `RegStatus` |
| 7 | `StudentProfile.class_name` là string tự do, không link `Organization` | 🟠 Low | Để sau |

---

## �📋 Task Breakdown (Các bước thực hiện)

### ✅ Phase 1: Cập nhật Model & Database *(ưu tiên cao — 1 migration duy nhất)*

- [x] **`activities/models.py` — `Activity`**: Thêm field `points = DecimalField(max_digits=5, decimal_places=2, default=0.00)`.
- [x] **`activities/models.py` — `ActivityRegistration.RegStatus`**: Thêm `ATTENDED` và `POINT_AWARDED`.
- [x] **`attendance/models.py` — `AttendanceRecord`**: Xóa field `activity` (FK thừa, redundant).
- [x] **`attendance/models.py` — `ActivityPoint`**: Thêm `point_category` FK, `awarded_by`, `awarded_at`.
- [x] **`attendance/models.py` — `ActivityPoint`**: Sửa unique constraint bỏ `reason`.
- [x] Chạy `makemigrations` và `migrate`.
- [x] Kiểm tra các views/queries đang dùng `record.activity` trực tiếp → chuyển sang `record.attendance_session.activity`.

### Phase 2: Cập nhật Form Create/Edit Activity

- [ ] Tại `templates/activities/form.html`: Thêm 1 input "Số điểm nhận được" (type number, step 0.01) nằm bên cạnh ComboBox "Mục điểm rèn luyện".
- [ ] Tại `activities/views.py`: Sửa `activity_create` và `activity_edit` để lấy trường `points` từ form và lưu vào database.
- [ ] Tại `templates/activities/detail.html` và `student_list.html`: Bổ sung hiển thị số điểm nhận được (ví dụ `CAT-C (5 điểm)`).

### Phase 3: Gom nhóm & Cải tổ UI duyệt điểm danh

- [ ] Xem UI hiện tại đang dùng duyệt điểm danh (`templates/attendance/records_list.html`, `session_detail.html` hoặc màn hình tương tự).
- [ ] Tạo một view chuyên dụng (ví dụ: `attendance/views.py` -> `activity_attendance_verify`) chuyên để xem tổng quan điểm danh của **Tất cả sinh viên trong 1 Activity**.
- [ ] **Logic Query**:
  - Lấy danh sách toàn bộ `AttendanceSession` của hoạt động đó (VD: 2 phiên).
  - Lấy danh sách toàn bộ sinh viên đã đăng ký / hoặc từng quét mã trong hoạt động.
  - Gắn dữ liệu từng sinh viên đi cùng array trạng thái điểm danh của họ: `[{session_id: 1, checked: True}, {session_id: 2, checked: False}]`.
- [ ] **UI Rendering**: Hiển thị bảng dạng Table Component:
  - Cột 1: Thông tin SV (Tên, MSSV).
  - Cột 2..N: Phản hồi của từng Phiên 1, Phiên 2 (Dấu Check Xanh / X Chữ thập).
  - Cột Cuối: Tổng kết "1/2 Phiên" (Màu Đỏ) hoặc "2/2 Phiên" (Màu Xanh), kèm **Nút Duyệt Cấp Điểm**.

### Phase 4: Xử lý chức năng Duyệt & Cấp ActivityPoint

- [x] Xây dựng Endpoint API / Form submit để "Duyệt" cho 1 hoặc nhiều sinh viên.
- [x] **Xử lý bên dưới**:
  - Update `ActivityRegistration.status` → `POINT_AWARDED`.
  - Update các record điểm danh của student đó thành `VERIFIED`.
  - Tạo mới `ActivityPoint` với `point_category` snapshot từ `activity.point_category`, `points = activity.points`, `awarded_by = request.user`, `awarded_at = now()`.
  - Ngăn ngừa cộng trùng điểm qua unique `(student, activity)`.
- [x] Bổ sung Nút "Duyệt Hàng Loạt" gộp những người "Đã điểm danh N/N phiên".
