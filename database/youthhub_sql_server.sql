-- SQL Server Database Schema for YouthHub
-- Generated based on d:\Code Project\Website Coding\Code - Đồ Án Cơ Sở 2\youth-hub\docs\bao_cao_do_an.md

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'YouthHub')
BEGIN
    CREATE DATABASE YouthHub;
END
GO

USE YouthHub;
GO

-- 1. users
CREATE TABLE users (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(150) NOT NULL UNIQUE,
    password NVARCHAR(128) NOT NULL,
    full_name NVARCHAR(255) NOT NULL,
    email NVARCHAR(254) NOT NULL UNIQUE,
    phone NVARCHAR(15) NULL,
    role NVARCHAR(20) NOT NULL DEFAULT 'STUDENT',
    avatar_url NVARCHAR(500) NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT chk_user_role CHECK (role IN ('ADMIN', 'STAFF', 'STUDENT')),
    CONSTRAINT chk_user_status CHECK (status IN ('ACTIVE', 'LOCKED'))
);

-- 2. student_profiles
CREATE TABLE student_profiles (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    student_code NVARCHAR(20) NOT NULL UNIQUE,
    faculty NVARCHAR(100) NOT NULL,
    class_name NVARCHAR(50) NULL,
    course_year NVARCHAR(20) NULL,
    CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. organizations
CREATE TABLE organizations (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    parent_id BIGINT NULL,
    type NVARCHAR(20) NOT NULL,
    name NVARCHAR(255) NOT NULL,
    code NVARCHAR(50) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NULL,
    status BIT NOT NULL DEFAULT 1,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_org_parent FOREIGN KEY (parent_id) REFERENCES organizations(id),
    CONSTRAINT chk_org_type CHECK (type IN ('UNION_SCHOOL', 'UNION_FACULTY', 'CLASS', 'CLUB'))
);

-- 4. organization_members
CREATE TABLE organization_members (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    organization_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    position NVARCHAR(100) NOT NULL,
    is_officer BIT NOT NULL DEFAULT 0,
    joined_at DATE NOT NULL DEFAULT GETDATE(),
    left_at DATE NULL,
    CONSTRAINT fk_member_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_member_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_org_user UNIQUE (organization_id, user_id)
);

-- 5. semesters
CREATE TABLE semesters (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    academic_year NVARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BIT NOT NULL DEFAULT 0,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT chk_semester_dates CHECK (start_date < end_date)
);

-- 6. activities
CREATE TABLE activities (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    organization_id BIGINT NOT NULL,
    semester_id BIGINT NULL,
    title NVARCHAR(255) NOT NULL,
    code NVARCHAR(50) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NULL,
    activity_type NVARCHAR(20) NOT NULL,
    start_time DATETIMEOFFSET NOT NULL,
    end_time DATETIMEOFFSET NOT NULL,
    location NVARCHAR(255) NOT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by BIGINT NOT NULL,
    approved_by BIGINT NULL,
    approved_at DATETIMEOFFSET NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_activity_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_activity_semester FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE SET NULL,
    CONSTRAINT fk_activity_creator FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT fk_activity_approver FOREIGN KEY (approved_by) REFERENCES users(id),
    CONSTRAINT chk_activity_type CHECK (activity_type IN ('VOLUNTEER', 'MEETING', 'ACADEMIC', 'OTHER')),
    CONSTRAINT chk_activity_status CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'ONGOING', 'DONE', 'CANCELED'))
);

-- 7. activity_registrations
CREATE TABLE activity_registrations (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    registered_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    status NVARCHAR(20) NOT NULL DEFAULT 'REGISTERED',
    CONSTRAINT fk_reg_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_reg_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_activity_student UNIQUE (activity_id, student_id),
    CONSTRAINT chk_reg_status CHECK (status IN ('REGISTERED', 'CANCELED', 'BANNED'))
);

-- 8. attendance_sessions
CREATE TABLE attendance_sessions (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    start_time DATETIMEOFFSET NOT NULL,
    end_time DATETIMEOFFSET NOT NULL,
    qr_token NVARCHAR(255) NOT NULL UNIQUE,
    requires_photo BIT NOT NULL DEFAULT 0,
    status NVARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_session_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT chk_session_status CHECK (status IN ('OPEN', 'CLOSED'))
);

-- 9. attendance_records
CREATE TABLE attendance_records (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    attendance_session_id BIGINT NOT NULL,
    student_id BIGINT NULL,
    entered_student_code NVARCHAR(20) NOT NULL,
    checkin_time DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    photo_path NVARCHAR(500) NULL,
    verified_by BIGINT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'PENDING',
    CONSTRAINT fk_record_session FOREIGN KEY (attendance_session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_record_student FOREIGN KEY (student_id) REFERENCES users(id),
    CONSTRAINT fk_record_verifier FOREIGN KEY (verified_by) REFERENCES users(id),
    CONSTRAINT chk_record_status CHECK (status IN ('PENDING', 'VERIFIED', 'REJECTED'))
);

-- Unique index for attendance_records to prevent duplicate checkins for logged-in students
CREATE UNIQUE INDEX uq_session_student ON attendance_records (attendance_session_id, student_id) WHERE student_id IS NOT NULL;

-- 10. ai_documents
CREATE TABLE ai_documents (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    created_by BIGINT NOT NULL,
    activity_id BIGINT NULL,
    doc_type NVARCHAR(20) NULL,
    title NVARCHAR(255) NULL,
    prompt NVARCHAR(MAX) NOT NULL,
    generated_content NVARCHAR(MAX) NOT NULL,
    model NVARCHAR(100) NOT NULL,
    tokens_input INT NULL,
    tokens_output INT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'RAW',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_ai_user FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT fk_ai_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL,
    CONSTRAINT chk_ai_doc_type CHECK (doc_type IN ('PLAN', 'REPORT', 'INVITATION', 'OTHER')),
    CONSTRAINT chk_ai_status CHECK (status IN ('RAW', 'DRAFT', 'EDITED', 'FINAL'))
);

-- 11. budgets
CREATE TABLE budgets (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    description NVARCHAR(MAX) NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    approved_by BIGINT NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_budget_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_approver FOREIGN KEY (approved_by) REFERENCES users(id),
    CONSTRAINT chk_budget_status CHECK (status IN ('DRAFT', 'APPROVED', 'REJECTED'))
);

-- 12. budget_items
CREATE TABLE budget_items (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    budget_id BIGINT NOT NULL,
    name NVARCHAR(255) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    category NVARCHAR(100) NOT NULL,
    note NVARCHAR(MAX) NULL,
    CONSTRAINT fk_item_budget FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
);

-- 13. tasks
CREATE TABLE tasks (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NULL,
    assigned_to BIGINT NOT NULL,
    due_date DATE NOT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'TODO',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_task_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_user FOREIGN KEY (assigned_to) REFERENCES users(id),
    CONSTRAINT chk_task_status CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE'))
);

-- 14. activity_points
CREATE TABLE activity_points (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    student_id BIGINT NOT NULL,
    activity_id BIGINT NOT NULL,
    points DECIMAL(5,2) NOT NULL,
    reason NVARCHAR(255) NOT NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_point_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_point_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT uq_student_activity_reason UNIQUE (student_id, activity_id, reason)
);

-- 15. audit_logs
CREATE TABLE audit_logs (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id BIGINT NULL,
    action NVARCHAR(100) NOT NULL,
    object_type NVARCHAR(100) NOT NULL,
    object_id BIGINT NOT NULL,
    ip_address NVARCHAR(45) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_log_user FOREIGN KEY (user_id) REFERENCES users(id)
);
