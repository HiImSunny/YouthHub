-- =============================================================================
-- YouthHub — SQL Server (T-SQL) Schema
-- Updated: 2026-03-03
-- Synchronized with Django models (Phase 1–5)
-- =============================================================================

-- Optional: create and use database
-- CREATE DATABASE YouthHub;
-- GO
-- USE YouthHub;
-- GO

-- =============================================================================
-- 1. users
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE users (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    username        NVARCHAR(150)   NOT NULL,
    password        NVARCHAR(128)   NOT NULL,
    full_name       NVARCHAR(255)   NOT NULL,
    email           NVARCHAR(254)   NOT NULL,
    phone           NVARCHAR(15)    NULL,
    role            NVARCHAR(10)    NOT NULL DEFAULT 'STUDENT'
                        CHECK (role IN ('ADMIN','STAFF','STUDENT')),
    avatar_url      NVARCHAR(500)   NULL,
    status          NVARCHAR(10)    NOT NULL DEFAULT 'ACTIVE'
                        CHECK (status IN ('ACTIVE','LOCKED')),
    -- Django auth fields
    is_staff        BIT             NOT NULL DEFAULT 0,
    is_active       BIT             NOT NULL DEFAULT 1,
    is_superuser    BIT             NOT NULL DEFAULT 0,
    last_login      DATETIMEOFFSET  NULL,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email    UNIQUE (email)
);
GO

-- =============================================================================
-- 2. student_profiles
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='student_profiles' AND xtype='U')
CREATE TABLE student_profiles (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    student_code    NVARCHAR(20)    NOT NULL,
    faculty         NVARCHAR(100)   NOT NULL,
    class_name      NVARCHAR(50)    NULL,
    course_year     NVARCHAR(20)    NULL,
    CONSTRAINT uq_sp_user         UNIQUE (user_id),
    CONSTRAINT uq_sp_student_code UNIQUE (student_code),
    CONSTRAINT fk_student_user    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
GO

-- =============================================================================
-- 3. organizations
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='organizations' AND xtype='U')
CREATE TABLE organizations (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    parent_id       BIGINT          NULL,
    type            NVARCHAR(20)    NOT NULL
                        CHECK (type IN ('UNION_SCHOOL','UNION_FACULTY','CLASS','CLUB')),
    name            NVARCHAR(255)   NOT NULL,
    code            NVARCHAR(50)    NOT NULL,
    description     NVARCHAR(MAX)   NULL,
    status          BIT             NOT NULL DEFAULT 1,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_org_code   UNIQUE (code),
    CONSTRAINT fk_org_parent FOREIGN KEY (parent_id) REFERENCES organizations(id)
);
GO

-- =============================================================================
-- 4. organization_members
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='organization_members' AND xtype='U')
CREATE TABLE organization_members (
    id                  BIGINT          IDENTITY(1,1) PRIMARY KEY,
    organization_id     BIGINT          NOT NULL,
    user_id             BIGINT          NOT NULL,
    position            NVARCHAR(100)   NOT NULL,
    is_officer          BIT             NOT NULL DEFAULT 0,
    joined_at           DATE            NOT NULL,
    left_at             DATE            NULL,
    CONSTRAINT uq_org_member  UNIQUE (organization_id, user_id),
    CONSTRAINT fk_member_org  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_member_user FOREIGN KEY (user_id)         REFERENCES users(id)        ON DELETE CASCADE
);
GO

-- =============================================================================
-- 5. semesters
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='semesters' AND xtype='U')
CREATE TABLE semesters (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(100)   NOT NULL,
    academic_year   NVARCHAR(20)    NOT NULL,
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    is_current      BIT             NOT NULL DEFAULT 0,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT chk_semester_dates CHECK (start_date < end_date)
);
GO

-- =============================================================================
-- 6. point_categories  [Phase 3 — Added]
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='point_categories' AND xtype='U')
CREATE TABLE point_categories (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(255)   NOT NULL,
    code            NVARCHAR(50)    NOT NULL,
    description     NVARCHAR(MAX)   NULL,
    is_active       BIT             NOT NULL DEFAULT 1,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_point_cat_code UNIQUE (code)
);
GO

-- =============================================================================
-- 7. activities
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='activities' AND xtype='U')
CREATE TABLE activities (
    id                  BIGINT          IDENTITY(1,1) PRIMARY KEY,
    organization_id     BIGINT          NOT NULL,
    semester_id         BIGINT          NULL,
    point_category_id   BIGINT          NULL,
    title               NVARCHAR(255)   NOT NULL,
    code                NVARCHAR(50)    NOT NULL,
    description         NVARCHAR(MAX)   NULL,
    activity_type       NVARCHAR(20)    NOT NULL
                            CHECK (activity_type IN ('VOLUNTEER','MEETING','ACADEMIC','OTHER')),
    start_time          DATETIMEOFFSET  NOT NULL,
    end_time            DATETIMEOFFSET  NOT NULL,
    location            NVARCHAR(255)   NOT NULL,
    status              NVARCHAR(20)    NOT NULL DEFAULT 'DRAFT'
                            CHECK (status IN ('DRAFT','PENDING','APPROVED','ONGOING','DONE','CANCELED')),
    created_by          BIGINT          NOT NULL,
    approved_by         BIGINT          NULL,
    approved_at         DATETIMEOFFSET  NULL,
    created_at          DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at          DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_activity_code       UNIQUE (code),
    CONSTRAINT fk_activity_org        FOREIGN KEY (organization_id)   REFERENCES organizations(id),
    CONSTRAINT fk_activity_semester   FOREIGN KEY (semester_id)       REFERENCES semesters(id),
    CONSTRAINT fk_activity_point_cat  FOREIGN KEY (point_category_id) REFERENCES point_categories(id),
    CONSTRAINT fk_activity_creator    FOREIGN KEY (created_by)        REFERENCES users(id),
    CONSTRAINT fk_activity_approver   FOREIGN KEY (approved_by)       REFERENCES users(id)
);
GO

-- =============================================================================
-- 8. activity_registrations
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='activity_registrations' AND xtype='U')
CREATE TABLE activity_registrations (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    activity_id     BIGINT          NOT NULL,
    student_id      BIGINT          NOT NULL,
    registered_at   DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    status          NVARCHAR(20)    NOT NULL DEFAULT 'REGISTERED'
                        CHECK (status IN ('REGISTERED','CANCELED','BANNED')),
    CONSTRAINT uq_activity_student UNIQUE (activity_id, student_id),
    CONSTRAINT fk_reg_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_reg_student  FOREIGN KEY (student_id)  REFERENCES users(id)      ON DELETE CASCADE
);
GO

-- =============================================================================
-- 9. budgets
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='budgets' AND xtype='U')
CREATE TABLE budgets (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    activity_id     BIGINT          NOT NULL,
    total_amount    DECIMAL(12,2)   NOT NULL,
    description     NVARCHAR(MAX)   NULL,
    status          NVARCHAR(20)    NOT NULL DEFAULT 'DRAFT'
                        CHECK (status IN ('DRAFT','APPROVED','REJECTED')),
    approved_by     BIGINT          NULL,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_budget_activity   UNIQUE (activity_id),
    CONSTRAINT fk_budget_activity   FOREIGN KEY (activity_id)  REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_approver   FOREIGN KEY (approved_by)  REFERENCES users(id)
);
GO

-- =============================================================================
-- 10. budget_items
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='budget_items' AND xtype='U')
CREATE TABLE budget_items (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    budget_id       BIGINT          NOT NULL,
    name            NVARCHAR(255)   NOT NULL,
    amount          DECIMAL(12,2)   NOT NULL,
    category        NVARCHAR(100)   NOT NULL,
    note            NVARCHAR(MAX)   NULL,
    CONSTRAINT fk_item_budget FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
);
GO

-- =============================================================================
-- 11. tasks
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='tasks' AND xtype='U')
CREATE TABLE tasks (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    activity_id     BIGINT          NOT NULL,
    title           NVARCHAR(255)   NOT NULL,
    description     NVARCHAR(MAX)   NULL,
    assigned_to     BIGINT          NOT NULL,
    due_date        DATE            NOT NULL,
    status          NVARCHAR(20)    NOT NULL DEFAULT 'TODO'
                        CHECK (status IN ('TODO','IN_PROGRESS','DONE')),
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_task_activity FOREIGN KEY (activity_id)  REFERENCES activities(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_user     FOREIGN KEY (assigned_to)  REFERENCES users(id)
);
GO

-- =============================================================================
-- 12. attendance_sessions
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='attendance_sessions' AND xtype='U')
CREATE TABLE attendance_sessions (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    activity_id     BIGINT          NOT NULL,
    name            NVARCHAR(100)   NOT NULL,
    start_time      DATETIMEOFFSET  NOT NULL,
    end_time        DATETIMEOFFSET  NOT NULL,
    qr_token        NVARCHAR(255)   NOT NULL,
    requires_photo  BIT             NOT NULL DEFAULT 0,
    status          NVARCHAR(10)    NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN','CLOSED')),
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_session_qr_token   UNIQUE (qr_token),
    CONSTRAINT fk_session_activity   FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);
GO

-- =============================================================================
-- 13. attendance_records
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='attendance_records' AND xtype='U')
CREATE TABLE attendance_records (
    id                      BIGINT          IDENTITY(1,1) PRIMARY KEY,
    attendance_session_id   BIGINT          NOT NULL,
    activity_id             BIGINT          NULL,
    student_id              BIGINT          NULL,
    entered_student_code    NVARCHAR(20)    NOT NULL,
    checkin_time            DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    photo_path              NVARCHAR(500)   NULL,
    verified_by             BIGINT          NULL,
    status                  NVARCHAR(20)    NOT NULL DEFAULT 'PENDING'
                                CHECK (status IN ('PENDING','VERIFIED','REJECTED')),
    approved_at             DATETIMEOFFSET  NULL,
    CONSTRAINT fk_record_session   FOREIGN KEY (attendance_session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_record_activity  FOREIGN KEY (activity_id)           REFERENCES activities(id),
    CONSTRAINT fk_record_student   FOREIGN KEY (student_id)            REFERENCES users(id),
    CONSTRAINT fk_record_verifier  FOREIGN KEY (verified_by)           REFERENCES users(id)
);
GO
-- Filtered unique index (partial index equivalent in SQL Server)
CREATE UNIQUE INDEX uq_session_student
    ON attendance_records (attendance_session_id, student_id)
    WHERE student_id IS NOT NULL;
GO

-- =============================================================================
-- 14. activity_points
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='activity_points' AND xtype='U')
CREATE TABLE activity_points (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    student_id      BIGINT          NOT NULL,
    activity_id     BIGINT          NOT NULL,
    points          DECIMAL(5,2)    NOT NULL,
    reason          NVARCHAR(255)   NOT NULL,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT uq_student_activity_reason UNIQUE (student_id, activity_id, reason),
    CONSTRAINT fk_point_student  FOREIGN KEY (student_id)  REFERENCES users(id)      ON DELETE CASCADE,
    CONSTRAINT fk_point_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);
GO

-- =============================================================================
-- 15. ai_documents
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ai_documents' AND xtype='U')
CREATE TABLE ai_documents (
    id                  BIGINT          IDENTITY(1,1) PRIMARY KEY,
    created_by          BIGINT          NOT NULL,
    activity_id         BIGINT          NULL,
    doc_type            NVARCHAR(20)    NULL
                            CHECK (doc_type IN ('PLAN','REPORT','INVITATION','OTHER')),
    title               NVARCHAR(255)   NULL,
    prompt              NVARCHAR(MAX)   NOT NULL,
    generated_content   NVARCHAR(MAX)   NOT NULL,
    model               NVARCHAR(100)   NOT NULL DEFAULT 'qwen2.5:7b',
    tokens_input        INT             NULL,
    tokens_output       INT             NULL,
    status              NVARCHAR(20)    NOT NULL DEFAULT 'RAW'
                            CHECK (status IN ('RAW','DRAFT','EDITED','FINAL')),
    created_at          DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at          DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_ai_user     FOREIGN KEY (created_by)  REFERENCES users(id),
    CONSTRAINT fk_ai_activity FOREIGN KEY (activity_id) REFERENCES activities(id)
);
GO

-- =============================================================================
-- 16. audit_logs  [Phase 5 — core.AuditLog]
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_logs' AND xtype='U')
CREATE TABLE audit_logs (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    user_id         BIGINT          NULL,
    action          NVARCHAR(20)    NOT NULL
                        CHECK (action IN ('CREATE','UPDATE','DELETE','APPROVE','REJECT','LOGIN','LOGOUT')),
    object_type     NVARCHAR(100)   NOT NULL,
    object_id       NVARCHAR(50)    NULL,
    object_repr     NVARCHAR(255)   NULL,
    changes         NVARCHAR(MAX)   NULL,  -- JSON string
    ip_address      NVARCHAR(45)    NULL,
    timestamp       DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_log_user FOREIGN KEY (user_id) REFERENCES users(id)
);
GO
CREATE INDEX idx_audit_action    ON audit_logs (action);
GO
CREATE INDEX idx_audit_timestamp ON audit_logs (timestamp DESC);
GO

-- =============================================================================
-- 17. ai_audit_logs  [Deprecated stub — ai_assistant.AuditLog]
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ai_audit_logs' AND xtype='U')
CREATE TABLE ai_audit_logs (
    id              BIGINT          IDENTITY(1,1) PRIMARY KEY,
    user_id         BIGINT          NULL,
    action          NVARCHAR(100)   NOT NULL,
    object_type     NVARCHAR(100)   NOT NULL,
    object_id       BIGINT          NOT NULL,
    ip_address      NVARCHAR(45)    NULL,
    created_at      DATETIMEOFFSET  NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT fk_ai_log_user FOREIGN KEY (user_id) REFERENCES users(id)
);
GO
