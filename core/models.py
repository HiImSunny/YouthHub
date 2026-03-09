from django.conf import settings
from django.db import models
import json


class Organization(models.Model):
    """
    Hierarchical organization structure (Doan truong, Doan khoa, Chi doan, CLB).
    Maps to table: organizations
    Self-referencing via parent_id for tree structure.
    """

    class OrgType(models.TextChoices):
        UNION_SCHOOL = 'UNION_SCHOOL', 'Đoàn trường'
        UNION_FACULTY = 'UNION_FACULTY', 'Đoàn khoa'
        CLASS = 'CLASS', 'Chi đoàn'
        CLUB = 'CLUB', 'Câu lạc bộ'

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    type = models.CharField(max_length=20, choices=OrgType.choices)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        verbose_name = 'Tổ chức'
        verbose_name_plural = 'Tổ chức'

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    @property
    def short_name(self):
        """Returns a shortened version of the organization name suitable for badges/QR display."""
        name_upper = self.name.upper()
        name_upper = name_upper.replace('ĐOÀN TRƯỜNG ĐẠI HỌC ', 'ĐH ')
        name_upper = name_upper.replace('ĐOÀN TRƯỜNG CAO ĐẲNG ', 'CĐ ')
        name_upper = name_upper.replace('ĐOÀN TRƯỜNG ', '')
        name_upper = name_upper.replace('ĐẠI HỌC ', 'ĐH ')
        return name_upper.strip()

    @property
    def root_org(self):
        """Returns the top-level parent organization."""
        current = self
        while current.parent is not None:
            current = current.parent
        return current
class OrganizationMember(models.Model):
    """
    Membership records linking users to organizations.
    Maps to table: organization_members
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    position = models.CharField(max_length=100)
    is_officer = models.BooleanField(default=False)
    joined_at = models.DateField()
    left_at = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'organization_members'
        verbose_name = 'Thành viên tổ chức'
        verbose_name_plural = 'Thành viên tổ chức'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'user'],
                name='unique_org_member',
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.organization} ({self.position})"


class Semester(models.Model):
    """
    Academic semester configuration.
    Maps to table: semesters
    """

    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='semesters',
        null=True,  # To allow migration running
        blank=True,
    )
    name = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'semesters'
        verbose_name = 'Học kỳ'
        verbose_name_plural = 'Học kỳ'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lt=models.F('end_date')),
                name='semester_date_check',
            ),
            models.UniqueConstraint(
                fields=['organization'],
                condition=models.Q(is_current=True),
                name='unique_current_semester_per_school',
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

    @property
    def dynamic_status(self):
        from django.utils import timezone
        today = timezone.localdate()
        if self.end_date < today:
            return 'CLOSED'
        if not self.is_current:
            if self.start_date > today:
                return 'UPCOMING'
            return 'CLOSED'
        return 'ONGOING'

    @property
    def dynamic_status_display(self):
        status_map = {
            'CLOSED': 'ĐÃ ĐÓNG',
            'UPCOMING': 'CHỜ MỞ',
            'ONGOING': 'ĐANG DIỄN RA',
        }
        return status_map[self.dynamic_status]

class AuditLog(models.Model):
    """
    System audit log for important CRUD operations.
    Maps to table: audit_logs
    Populated via Django Signals.
    """

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Tạo mới'
        UPDATE = 'UPDATE', 'Cập nhật'
        DELETE = 'DELETE', 'Xóa'
        APPROVE = 'APPROVE', 'Phê duyệt'
        REJECT = 'REJECT', 'Từ chối'
        LOGIN = 'LOGIN', 'Đăng nhập'
        LOGOUT = 'LOGOUT', 'Đăng xuất'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    # Target object info
    object_type = models.CharField(max_length=100)   # e.g. 'Activity'
    object_id = models.CharField(max_length=50, blank=True, null=True)
    object_repr = models.CharField(max_length=255, blank=True, null=True)
    # Detail diff (JSON)
    changes = models.TextField(blank=True, null=True)
    # Request metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%d/%m/%Y %H:%M}] {self.user} {self.action} {self.object_type}"

    def set_changes(self, data: dict):
        """Serialize changes dict to JSON string."""
        self.changes = json.dumps(data, ensure_ascii=False, default=str)

    def get_changes(self):
        """Deserialize JSON changes to dict."""
        if self.changes:
            return json.loads(self.changes)
        return {}
