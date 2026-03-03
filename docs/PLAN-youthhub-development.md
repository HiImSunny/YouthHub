---
title: Kế hoạch triển khai dự án YouthHub
description: Kế hoạch chi tiết theo các Phase dựa trên thiết kế Database và chức năng phần mềm.
status: DRAFT
---

# KẾ HOẠCH PHÁT TRIỂN YOUTHHUB

## Tổng quan dự án (The "Why")

- **Tên dự án:** YouthHub - Nền tảng quản lý hoạt động Đoàn - Hội sinh viên tích hợp AI.
- **Mục tiêu:** Số hóa quy trình quản lý tổ chức, thành viên, phê duyệt hoạt động, điểm danh QR/Selfie, quản lý ngân sách và hỗ trợ AI soạn thảo văn bản hành chính (Qwen 2.5). Không gian làm việc dùng chung cho Admin, Cán bộ Đoàn-Hội và Sinh viên.
- **Tech Stack:**
  - Backend: Python + Django (MTV)
  - Database: PostgreSQL
  - Asynchronous Tasks: Celery + Redis
  - AI Local: Ollama (Qwen 2.5)
  - Frontend: Django Templates + Tailwind CSS
- **Tài liệu tham khảo chính:** `docs/bao_cao_do_an.md`, `database/youthhub_mysql.sql`.

---

## Các Giai đoạn Triển khai (Milestones)

Dự án được cắt nhỏ thành 5 Phase độc lập theo nguyên tắc Dependency-First (Ưu tiên những phần phụ thuộc trước).

### Phase 1: Skeleton & Core Database (Móng & Khung)

**Mục tiêu:** Khởi tạo project Django, thiết lập PostgreSQL, cấu hình Model và xác thực người dùng.

- Khởi tạo project Django `youthhub`.
- Thiết lập kết nối PostgreSQL (sử dụng psycopg2).
- Tạo ứng dụng `users` và cấu hình Custom User Model (bảng `users` với Role-Based).
- Tạo ứng dụng `core` lưu trữ các model tổ chức và hệ thống (bảng `organizations`, `semesters`, `organization_members`).
- Tạo ứng dụng `student_profiles` (quan hệ 1:1 với `users`).
- Hoàn thiện toàn bộ các models theo đúng Entity Relationship Diagram (ERD).
- Tạo dữ liệu giả (Seeder/Fixtures) cơ bản (Tạo Admin, 1-2 Tổ chức Đoàn, 1 Học kỳ).

### Phase 2: Quản lý Hoạt động & Đăng ký (Core Business Logic)

**Mục tiêu:** Xây dựng tính năng cốt lõi là Quản lý Vòng đời sự kiện.

- Tạo ứng dụng `activities` (bảng `activities`, `activity_registrations`, `tasks`, `budgets`, `budget_items`).
- Xây dựng giao diện danh sách hoạt động, thêm/sửa/xóa hoạt động (Tailwind CSS + Django Templates).
- Luồng phê duyệt hoạt động (Draft -> Pending -> Approved).
- Mở form đăng ký cho Sinh viên, xác nhận trạng thái.

### Phase 3: Hệ thống Điểm danh Thông minh (Attendance System)

**Mục tiêu:** Xử lý luồng sinh mã QR, điểm danh trực tuyến và lưu trữ minh chứng.

- Tạo ứng dụng `attendance` (bảng `attendance_sessions`, `attendance_records`, `activity_points`).
- Cơ chế tạo phiên điểm danh & sinh mã QR động.
- Giao diện quét mã / nhập mã SV điểm danh.
- Tích hợp Celery/Redis để xử lý lưu hình ảnh selfie bất đồng bộ (giảm tải cho server).
- Cán bộ duyệt điểm danh và tự động cộng điểm rèn luyện `activity_points`.

### Phase 4: Trợ lý AI Soạn thảo (AI Assistant)

**Mục tiêu:** Hỗ trợ cán bộ tạo nhanh văn bản (Kế hoạch, Báo cáo) qua Ollama.

- Tạo ứng dụng `ai_assistant` (bảng `ai_documents`).
- Viết API kết nối tới local Ollama instance (sử dụng thư viện `ollama` hoặc `requests`).
- Thiết kế Prompt Engineering (Kế hoạch chương trình, Báo cáo sự kiện).
- Giao diện: Cửa sổ chat/form sinh văn bản, lưu nháp, chỉnh sửa.

### Phase 5: Phân quyền, Thống kê & Hoàn thiện (Audit, Dashboard)

**Mục tiêu:** Tạo Dashboard trực quan, bảo mật RBAC, Audit Log.

- Áp dụng các Middleware / Decorator kiểm tra quyền truy cập (Admin / Staff / Student).
- Xây dựng Dashboard thống kê (Tỷ lệ tham gia, số sự kiện, chi phí) bằng Chart.js.
- Viết hệ thống Ghi log (`audit_logs`) bằng Django Signals cho các thao tác quan trọng (Create, Update, Delete).
- Fix bug, làm đẹp UI/UX, hướng dẫn cài đặt (README).

---

## Verifiably (Tiêu chí nghiệm thu chung)

- Không hardcode thông tin nhạy cảm.
- UI tương thích Mobile (Responsive Tailwind).
- Model tuân thủ đúng tên field & relation trong file SQL đã làm.
