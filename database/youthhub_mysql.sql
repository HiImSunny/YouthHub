-- MySQL Database Schema for YouthHub
-- Generated based on d:\Code Project\Website Coding\Code - Đồ Án Cơ Sở 2\youth-hub\docs\bao_cao_do_an.md

CREATE DATABASE IF NOT EXISTS youthhub DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE youthhub;

-- 1. users
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    phone VARCHAR(15) NULL,
    role ENUM('ADMIN', 'STAFF', 'STUDENT') NOT NULL DEFAULT 'STUDENT',
    avatar_url VARCHAR(500) NULL,
    status ENUM('ACTIVE', 'LOCKED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. student_profiles
CREATE TABLE student_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    student_code VARCHAR(20) NOT NULL UNIQUE,
    faculty VARCHAR(100) NOT NULL,
    class_name VARCHAR(50) NULL,
    course_year VARCHAR(20) NULL,
    CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. organizations
CREATE TABLE organizations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT NULL,
    type ENUM('UNION_SCHOOL', 'UNION_FACULTY', 'CLASS', 'CLUB') NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_org_parent FOREIGN KEY (parent_id) REFERENCES organizations(id)
);

-- 4. organization_members
CREATE TABLE organization_members (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    position VARCHAR(100) NOT NULL,
    is_officer BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at DATE NOT NULL,
    left_at DATE NULL,
    CONSTRAINT fk_member_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_member_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_org_user (organization_id, user_id)
);

-- 5. semesters
CREATE TABLE semesters (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_semester_dates CHECK (start_date < end_date)
);

-- 6. activities
CREATE TABLE activities (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NOT NULL,
    semester_id BIGINT NULL,
    title VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NULL,
    activity_type ENUM('VOLUNTEER', 'MEETING', 'ACADEMIC', 'OTHER') NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    location VARCHAR(255) NOT NULL,
    status ENUM('DRAFT', 'PENDING', 'APPROVED', 'ONGOING', 'DONE', 'CANCELED') NOT NULL DEFAULT 'DRAFT',
    created_by BIGINT NOT NULL,
    approved_by BIGINT NULL,
    approved_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_activity_semester FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE SET NULL,
    CONSTRAINT fk_activity_creator FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT fk_activity_approver FOREIGN KEY (approved_by) REFERENCES users(id)
);

-- 7. activity_registrations
CREATE TABLE activity_registrations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('REGISTERED', 'CANCELED', 'BANNED') NOT NULL DEFAULT 'REGISTERED',
    CONSTRAINT fk_reg_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_reg_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_activity_student (activity_id, student_id)
);

-- 8. attendance_sessions
CREATE TABLE attendance_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    qr_token VARCHAR(255) NOT NULL UNIQUE,
    requires_photo BOOLEAN NOT NULL DEFAULT FALSE,
    status ENUM('OPEN', 'CLOSED') NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_session_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);

-- 9. attendance_records
CREATE TABLE attendance_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    attendance_session_id BIGINT NOT NULL,
    student_id BIGINT NULL,
    entered_student_code VARCHAR(20) NOT NULL,
    checkin_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    photo_path VARCHAR(500) NULL,
    verified_by BIGINT NULL,
    status ENUM('PENDING', 'VERIFIED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    CONSTRAINT fk_record_session FOREIGN KEY (attendance_session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_record_student FOREIGN KEY (student_id) REFERENCES users(id),
    CONSTRAINT fk_record_verifier FOREIGN KEY (verified_by) REFERENCES users(id)
);

-- Unique index for attendance_records to prevent duplicate checkins for logged-in students
-- MySQL context: Unique index with NULL allows multiple NULLs by default, which is correct here.
ALTER TABLE attendance_records ADD UNIQUE KEY uq_session_student (attendance_session_id, student_id);

-- 10. ai_documents
CREATE TABLE ai_documents (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_by BIGINT NOT NULL,
    activity_id BIGINT NULL,
    doc_type ENUM('PLAN', 'REPORT', 'INVITATION', 'OTHER') NULL,
    title VARCHAR(255) NULL,
    prompt TEXT NOT NULL,
    generated_content LONGTEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_input INT NULL,
    tokens_output INT NULL,
    status ENUM('RAW', 'DRAFT', 'EDITED', 'FINAL') NOT NULL DEFAULT 'RAW',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ai_user FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT fk_ai_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL
);

-- 11. budgets
CREATE TABLE budgets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    description TEXT NULL,
    status ENUM('DRAFT', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'DRAFT',
    approved_by BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_budget_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_approver FOREIGN KEY (approved_by) REFERENCES users(id)
);

-- 12. budget_items
CREATE TABLE budget_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    budget_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    category VARCHAR(100) NOT NULL,
    note TEXT NULL,
    CONSTRAINT fk_item_budget FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
);

-- 13. tasks
CREATE TABLE tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    assigned_to BIGINT NOT NULL,
    due_date DATE NOT NULL,
    status ENUM('TODO', 'IN_PROGRESS', 'DONE') NOT NULL DEFAULT 'TODO',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_task_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_user FOREIGN KEY (assigned_to) REFERENCES users(id)
);

-- 14. activity_points
CREATE TABLE activity_points (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT NOT NULL,
    activity_id BIGINT NOT NULL,
    points DECIMAL(5,2) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_point_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_point_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    UNIQUE KEY uq_student_activity_reason (student_id, activity_id, reason)
);

-- 15. audit_logs
CREATE TABLE audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NULL,
    action VARCHAR(100) NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    object_id BIGINT NOT NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_user FOREIGN KEY (user_id) REFERENCES users(id)
);
