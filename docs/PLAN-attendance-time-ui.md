# PLAN: Tối ưu UI hiển thị Mốc Thời Gian Điểm Danh

## Context & Objectives

- **Vấn đề**:
  1. Trang danh sách `/attendance/`: Hiện mốc kết thúc chỉ có giờ (`H:i`), không có ngày, nếu băng qua ngày hôm sau sẽ không ai biết được.
  2. Trang chi tiết (`/attendance/3/`) và quét QR (`/attendance/3/qr/`): Định dạng rập khuôn `23:39 05/03/2026 — 23:39 06/03/2026` dính liền 1 cục cùng chung 1 màu, chữ số dài gây rối mắt, khó phân biệt giữa hai phần Bắt đầu và Kết thúc.
- **Mục tiêu**:
  - Viết lại UI phần hiển thị ngày giờ mang đậm chất Neo Brutalism (chia khối/nhãn tag màu mạnh) thay vì chỉ nhét vào 1 String tĩnh.
  - Hiển thị ngày và giờ độc lập, nếu chung 1 ngày có thể thu gọn, nếu khác ngày sẽ show rõ ngày kết thúc. Ở màn hình to thì phân mảng (BẮT ĐẦU - KẾT THÚC).

---

## Task Breakdown

### Phase 1: Sessions List UI

- **Mục tiêu**: Bổ sung ngày vào mốc kết thúc, tách ngày và giờ ra để dễ nhìn gọn gàng.
- **Files**:
  - `templates/attendance/sessions.html`:
    - Thay `{{ session.start_time|date:"d/m/Y H:i" }} → {{ session.end_time|date:"H:i" }}` thành 2 dòng riêng biệt: Dòng 1 là ngày (`d/m/Y`), Dòng 2 là giờ (`H:i → H:i`).
    - Hoặc thêm label "TỪ" - "ĐẾN" bằng các cụm tag CSS nhỏ.

### Phase 2: Session Detail & Checkin Box UI

- **Mục tiêu**: Tách hai mốc thành hai block màu sắc đối lập (ví dụ đen - cam) hoặc chia vách ngăn để mắt người dùng bắt được thông tin nhanh hơn.
- **Files**:
  - `templates/attendance/session_detail.html`:
    - Thay dòng `<p>... — ...</p>` thành một thẻ div `<div class="flex gap-2">` bọc bởi 2 cục label hiển thị.
    - Cục 1 (BẮT ĐẦU): Nền cam chữ đen (`bg-primary text-black px-2 py-1`).
    - Cục 2 (KẾT THÚC): Nền đen chữ trắng (`bg-black text-white px-2 py-1`).

### Phase 3: QR Display UI

- **Mục tiêu**: Khắc phục lỗi rập khuôn dài của dòng chữ trong trang QR full màn hình để sinh viên và giáo viên dễ nắm bắt phiên này kéo dài đến bao giờ.
- **Files**:
  - `templates/attendance/qr_display.html`:
    - Block "THỜI GIAN" sẽ được viết lại dưới dạng Grid hoặc 2 dòng có nhãn.
    - Dòng trên chứa tag `BẮT ĐẦU` (border đen, nền cam) + Giờ to (font Mono) + Ngày mờ (Slate).
    - Dòng dưới chứa tag `KẾT THÚC` (border đen, nền đen) + Giờ to + Ngày mờ.

---

## Verification Checklist

- [ ] Trang danh sách phiên điểm danh: Ngày giờ không bị mập mờ, hiểu rõ ngay ngày đóng / ngày mở nếu phiên kéo dài qua đêm.
- [ ] Trang chi tiết phiên: Thời gian tách biệt thành label rõ, không còn dính chung 1 chuỗi ký tự.
- [ ] Trang QR Full màn hình: Hai mốc Bắt Đầu và Kết Thúc tạo ra tầng lớp Typography rõ ràng, nhấn mạnh yếu tố `Giờ` và đi kèm nhãn tag Brutalism.

---

## Agent Assignments

- **Antigravity Agent**: Sử dụng bộ công cụ `replace_file_content` hoặc `multi_replace_file_content` để chèn block HTML/CSS có sẵn các layout dạng flex/gap vào các view Tương ứng.
