-- =============================================================================
-- YouthHub — MySQL Schema
-- Updated: 2026-03-03
-- Synchronized with Django models (Phase 1–5)
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- =============================================================================
-- 1. users
-- =============================================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `username`      VARCHAR(150)    NOT NULL UNIQUE,
    `password`      VARCHAR(128)    NOT NULL,
    `full_name`     VARCHAR(255)    NOT NULL,
    `email`         VARCHAR(254)    NOT NULL UNIQUE,
    `phone`         VARCHAR(15)     NULL,
    `role`          ENUM('ADMIN','STAFF','STUDENT') NOT NULL DEFAULT 'STUDENT',
    `avatar_url`    VARCHAR(500)    NULL,
    `status`        ENUM('ACTIVE','LOCKED')         NOT NULL DEFAULT 'ACTIVE',
    -- Django auth fields
    `is_staff`      TINYINT(1)      NOT NULL DEFAULT 0,
    `is_active`     TINYINT(1)      NOT NULL DEFAULT 1,
    `is_superuser`  TINYINT(1)      NOT NULL DEFAULT 0,
    `last_login`    DATETIME        NULL,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 2. student_profiles
-- =============================================================================
CREATE TABLE IF NOT EXISTS `student_profiles` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`       BIGINT          NOT NULL UNIQUE,
    `student_code`  VARCHAR(20)     NOT NULL UNIQUE,
    `faculty`       VARCHAR(100)    NOT NULL,
    `class_name`    VARCHAR(50)     NULL,
    `course_year`   VARCHAR(20)     NULL,
    CONSTRAINT `fk_student_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 3. organizations
-- =============================================================================
CREATE TABLE IF NOT EXISTS `organizations` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `parent_id`     BIGINT          NULL,
    `type`          ENUM('UNION_SCHOOL','UNION_FACULTY','CLASS','CLUB') NOT NULL,
    `name`          VARCHAR(255)    NOT NULL,
    `code`          VARCHAR(50)     NOT NULL UNIQUE,
    `description`   TEXT            NULL,
    `status`        TINYINT(1)      NOT NULL DEFAULT 1,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_org_parent` FOREIGN KEY (`parent_id`) REFERENCES `organizations`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 4. organization_members
-- =============================================================================
CREATE TABLE IF NOT EXISTS `organization_members` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `organization_id`   BIGINT          NOT NULL,
    `user_id`           BIGINT          NOT NULL,
    `position`          VARCHAR(100)    NOT NULL,
    `is_officer`        TINYINT(1)      NOT NULL DEFAULT 0,
    `joined_at`         DATE            NOT NULL,
    `left_at`           DATE            NULL,
    CONSTRAINT `fk_member_org`  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_member_user` FOREIGN KEY (`user_id`)         REFERENCES `users`(`id`)        ON DELETE CASCADE,
    CONSTRAINT `uq_org_user` UNIQUE (`organization_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 5. semesters
-- =============================================================================
CREATE TABLE IF NOT EXISTS `semesters` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name`          VARCHAR(100)    NOT NULL,
    `academic_year` VARCHAR(20)     NOT NULL,
    `start_date`    DATE            NOT NULL,
    `end_date`      DATE            NOT NULL,
    `is_current`    TINYINT(1)      NOT NULL DEFAULT 0,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `chk_semester_dates` CHECK (`start_date` < `end_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 6. point_categories  [Phase 3 — Added]
-- =============================================================================
CREATE TABLE IF NOT EXISTS `point_categories` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name`          VARCHAR(255)    NOT NULL,
    `code`          VARCHAR(50)     NOT NULL UNIQUE,
    `description`   TEXT            NULL,
    `is_active`     TINYINT(1)      NOT NULL DEFAULT 1,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 7. activities
-- =============================================================================
CREATE TABLE IF NOT EXISTS `activities` (
    `id`                    BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `organization_id`       BIGINT          NOT NULL,
    `semester_id`           BIGINT          NULL,
    `point_category_id`     BIGINT          NULL,
    `title`                 VARCHAR(255)    NOT NULL,
    `code`                  VARCHAR(50)     NOT NULL UNIQUE,
    `description`           TEXT            NULL,
    `activity_type`         ENUM('VOLUNTEER','MEETING','ACADEMIC','OTHER') NOT NULL,
    `start_time`            DATETIME        NOT NULL,
    `end_time`              DATETIME        NOT NULL,
    `location`              VARCHAR(255)    NOT NULL,
    `status`                ENUM('DRAFT','PENDING','APPROVED','ONGOING','DONE','CANCELED') NOT NULL DEFAULT 'DRAFT',
    `created_by`            BIGINT          NOT NULL,
    `approved_by`           BIGINT          NULL,
    `approved_at`           DATETIME        NULL,
    `created_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_activity_org`        FOREIGN KEY (`organization_id`)   REFERENCES `organizations`(`id`),
    CONSTRAINT `fk_activity_semester`   FOREIGN KEY (`semester_id`)       REFERENCES `semesters`(`id`)         ON DELETE SET NULL,
    CONSTRAINT `fk_activity_point_cat`  FOREIGN KEY (`point_category_id`) REFERENCES `point_categories`(`id`)  ON DELETE SET NULL,
    CONSTRAINT `fk_activity_creator`    FOREIGN KEY (`created_by`)        REFERENCES `users`(`id`),
    CONSTRAINT `fk_activity_approver`   FOREIGN KEY (`approved_by`)       REFERENCES `users`(`id`)             ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 8. activity_registrations
-- =============================================================================
CREATE TABLE IF NOT EXISTS `activity_registrations` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `activity_id`   BIGINT          NOT NULL,
    `student_id`    BIGINT          NOT NULL,
    `registered_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status`        ENUM('REGISTERED','CANCELED','BANNED') NOT NULL DEFAULT 'REGISTERED',
    CONSTRAINT `fk_reg_activity` FOREIGN KEY (`activity_id`) REFERENCES `activities`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reg_student`  FOREIGN KEY (`student_id`)  REFERENCES `users`(`id`)      ON DELETE CASCADE,
    CONSTRAINT `uq_activity_student` UNIQUE (`activity_id`, `student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 9. budgets
-- =============================================================================
CREATE TABLE IF NOT EXISTS `budgets` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `activity_id`   BIGINT          NOT NULL UNIQUE,
    `total_amount`  DECIMAL(12,2)   NOT NULL,
    `description`   TEXT            NULL,
    `status`        ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
    `approved_by`   BIGINT          NULL,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_budget_activity` FOREIGN KEY (`activity_id`)  REFERENCES `activities`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_budget_approver` FOREIGN KEY (`approved_by`)  REFERENCES `users`(`id`)      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 10. budget_items
-- =============================================================================
CREATE TABLE IF NOT EXISTS `budget_items` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `budget_id`     BIGINT          NOT NULL,
    `name`          VARCHAR(255)    NOT NULL,
    `amount`        DECIMAL(12,2)   NOT NULL,
    `category`      VARCHAR(100)    NOT NULL,
    `note`          TEXT            NULL,
    CONSTRAINT `fk_item_budget` FOREIGN KEY (`budget_id`) REFERENCES `budgets`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 11. tasks
-- =============================================================================
CREATE TABLE IF NOT EXISTS `tasks` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `activity_id`   BIGINT          NOT NULL,
    `title`         VARCHAR(255)    NOT NULL,
    `description`   TEXT            NULL,
    `assigned_to`   BIGINT          NOT NULL,
    `due_date`      DATE            NOT NULL,
    `status`        ENUM('TODO','IN_PROGRESS','DONE') NOT NULL DEFAULT 'TODO',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_task_activity` FOREIGN KEY (`activity_id`)  REFERENCES `activities`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_user`     FOREIGN KEY (`assigned_to`)  REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 12. attendance_sessions
-- =============================================================================
CREATE TABLE IF NOT EXISTS `attendance_sessions` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `activity_id`       BIGINT          NOT NULL,
    `name`              VARCHAR(100)    NOT NULL,
    `start_time`        DATETIME        NOT NULL,
    `end_time`          DATETIME        NOT NULL,
    `qr_token`          VARCHAR(255)    NOT NULL UNIQUE,
    `requires_photo`    TINYINT(1)      NOT NULL DEFAULT 0,
    `status`            ENUM('OPEN','CLOSED') NOT NULL DEFAULT 'OPEN',
    `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_session_activity` FOREIGN KEY (`activity_id`) REFERENCES `activities`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 13. attendance_records
-- =============================================================================
CREATE TABLE IF NOT EXISTS `attendance_records` (
    `id`                        BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `attendance_session_id`     BIGINT          NOT NULL,
    `activity_id`               BIGINT          NULL,
    `student_id`                BIGINT          NULL,
    `entered_student_code`      VARCHAR(20)     NOT NULL,
    `checkin_time`              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `photo_path`                VARCHAR(500)    NULL,
    `verified_by`               BIGINT          NULL,
    `status`                    ENUM('PENDING','VERIFIED','REJECTED') NOT NULL DEFAULT 'PENDING',
    `approved_at`               DATETIME        NULL,
    CONSTRAINT `fk_record_session`   FOREIGN KEY (`attendance_session_id`) REFERENCES `attendance_sessions`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_record_activity`  FOREIGN KEY (`activity_id`)           REFERENCES `activities`(`id`)          ON DELETE CASCADE,
    CONSTRAINT `fk_record_student`   FOREIGN KEY (`student_id`)            REFERENCES `users`(`id`)               ON DELETE SET NULL,
    CONSTRAINT `fk_record_verifier`  FOREIGN KEY (`verified_by`)           REFERENCES `users`(`id`)               ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Partial unique: MySQL không hỗ trợ partial index, dùng trigger hoặc app-level
CREATE UNIQUE INDEX `uq_session_student_nn` ON `attendance_records` (`attendance_session_id`, `student_id`);

-- =============================================================================
-- 14. activity_points
-- =============================================================================
CREATE TABLE IF NOT EXISTS `activity_points` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `student_id`    BIGINT          NOT NULL,
    `activity_id`   BIGINT          NOT NULL,
    `points`        DECIMAL(5,2)    NOT NULL,
    `reason`        VARCHAR(255)    NOT NULL,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_point_student`  FOREIGN KEY (`student_id`)  REFERENCES `users`(`id`)      ON DELETE CASCADE,
    CONSTRAINT `fk_point_activity` FOREIGN KEY (`activity_id`) REFERENCES `activities`(`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_student_activity_reason` UNIQUE (`student_id`, `activity_id`, `reason`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 15. ai_documents
-- =============================================================================
CREATE TABLE IF NOT EXISTS `ai_documents` (
    `id`                    BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `created_by`            BIGINT          NOT NULL,
    `activity_id`           BIGINT          NULL,
    `doc_type`              ENUM('PLAN','REPORT','INVITATION','OTHER') NULL,
    `title`                 VARCHAR(255)    NULL,
    `prompt`                TEXT            NOT NULL,
    `generated_content`     TEXT            NOT NULL,
    `model`                 VARCHAR(100)    NOT NULL DEFAULT 'qwen2.5:7b',
    `tokens_input`          INT             NULL,
    `tokens_output`         INT             NULL,
    `status`                ENUM('RAW','DRAFT','EDITED','FINAL') NOT NULL DEFAULT 'RAW',
    `created_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ai_user`     FOREIGN KEY (`created_by`)  REFERENCES `users`(`id`)      ON DELETE CASCADE,
    CONSTRAINT `fk_ai_activity` FOREIGN KEY (`activity_id`) REFERENCES `activities`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 16. audit_logs  [Phase 5 — core.AuditLog]
-- =============================================================================
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`       BIGINT          NULL,
    `action`        ENUM('CREATE','UPDATE','DELETE','APPROVE','REJECT','LOGIN','LOGOUT') NOT NULL,
    `object_type`   VARCHAR(100)    NOT NULL,
    `object_id`     VARCHAR(50)     NULL,
    `object_repr`   VARCHAR(255)    NULL,
    `changes`       TEXT            NULL,
    `ip_address`    VARCHAR(45)     NULL,
    `timestamp`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_log_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_audit_action`    (`action`),
    INDEX `idx_audit_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 17. ai_audit_logs  [Deprecated stub — ai_assistant.AuditLog]
-- =============================================================================
CREATE TABLE IF NOT EXISTS `ai_audit_logs` (
    `id`            BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`       BIGINT          NULL,
    `action`        VARCHAR(100)    NOT NULL,
    `object_type`   VARCHAR(100)    NOT NULL,
    `object_id`     BIGINT          NOT NULL,
    `ip_address`    VARCHAR(45)     NULL,
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ai_log_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
