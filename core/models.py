from django.conf import settings
from django.db import models


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
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"
