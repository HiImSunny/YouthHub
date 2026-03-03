"""
One-time migration script: rename old audit_logs table to ai_audit_logs,
then create new audit_logs table for core.AuditLog.

Run with: python fix_audit_tables.py
"""
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youthhub.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check if audit_logs still exists (may already be renamed)
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'audit_logs'
        );
    """)
    audit_exists = cursor.fetchone()[0]

    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'ai_audit_logs'
        );
    """)
    ai_audit_exists = cursor.fetchone()[0]

    print(f"audit_logs exists: {audit_exists}")
    print(f"ai_audit_logs exists: {ai_audit_exists}")

    if audit_exists and not ai_audit_exists:
        print("Renaming audit_logs -> ai_audit_logs ...")
        cursor.execute("ALTER TABLE audit_logs RENAME TO ai_audit_logs;")
        print("Done rename.")
    elif not audit_exists and ai_audit_exists:
        print("ai_audit_logs already exists, audit_logs is gone. Good.")
    elif audit_exists and ai_audit_exists:
        print("Both exist! Dropping old audit_logs (it was from ai_assistant).")
        cursor.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")

    # Now create the NEW core audit_logs table
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'audit_logs'
        );
    """)
    audit_exists_now = cursor.fetchone()[0]

    if not audit_exists_now:
        print("Creating new core audit_logs table ...")
        cursor.execute("""
            CREATE TABLE audit_logs (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                action VARCHAR(20) NOT NULL,
                object_type VARCHAR(100) NOT NULL,
                object_id VARCHAR(50),
                object_repr VARCHAR(255),
                changes TEXT,
                ip_address INET,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cursor.execute("CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);")
        cursor.execute("CREATE INDEX idx_audit_logs_action ON audit_logs(action);")
        cursor.execute("CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);")
        print("Created audit_logs successfully!")
    else:
        print("audit_logs already exists. Skipping creation.")

print("All done!")
