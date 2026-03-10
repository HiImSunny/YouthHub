from django.conf import settings
from django.db import models


class PointCategory(models.Model):
    """
    Categories for training/activity points.
    Maps to table: point_categories
    """
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='point_categories',
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'point_categories'
        verbose_name = 'Mục điểm rèn luyện'
        verbose_name_plural = 'Mục điểm rèn luyện'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_point_category',
            )
        ]
        ordering = ['organization', 'code']

    def __str__(self):
        return f"[{self.organization.code}] {self.code} - {self.name}"




class Activity(models.Model):
    """
    Full lifecycle of a Doan-Hoi activity/event.
    Maps to table: activities
    Status flow: DRAFT -> PENDING -> APPROVED -> ONGOING -> DONE / CANCELED
    """

    class ActivityType(models.TextChoices):
        VOLUNTEER = 'VOLUNTEER', 'Tình nguyện'
        MEETING = 'MEETING', 'Sinh hoạt'
        ACADEMIC = 'ACADEMIC', 'Học thuật'
        OTHER = 'OTHER', 'Khác'

    class ActivityStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Nháp'
        PENDING = 'PENDING', 'Chờ duyệt'
        APPROVED = 'APPROVED', 'Đã duyệt'
        ONGOING = 'ONGOING', 'Đang diễn ra'
        DONE = 'DONE', 'Đã kết thúc'
        CANCELED = 'CANCELED', 'Đã hủy'

    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='activities',
    )
    semester = models.ForeignKey(
        'core.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    point_category = models.ForeignKey(
        'PointCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text='Số điểm rèn luyện nhận được khi hoàn thành hoạt động',
    )
    max_participants = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Giới hạn số lượng sinh viên đăng ký. Để trống nếu không giới hạn.',
    )
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.DRAFT,
    )
    budget_info = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Tổng hợp dự trù kinh phí'
    )
    tasks_info = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text='Danh sách task công việc'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_activities',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_activities',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activities'
        verbose_name = 'Hoạt động'
        verbose_name_plural = 'Hoạt động'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ActivityParticipation(models.Model):
    """
    Unified record for a student's participation in an activity.
    Replaces: ActivityRegistration, AttendanceRecord, ActivityPoint.
    Maps to table: activity_participations
    """

    class PartStatus(models.TextChoices):
        REGISTERED = 'REGISTERED', 'Đã đăng ký'
        ATTENDED = 'ATTENDED', 'Đã tham gia (Chờ duyệt)'
        VERIFIED = 'VERIFIED', 'Đã duyệt tham gia'
        REJECTED = 'REJECTED', 'Từ chối'
        CANCELED = 'CANCELED', 'Đã hủy'
        BANNED = 'BANNED', 'Bị cấm'

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='participations',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_participations',
    )
    entered_student_code = models.CharField(max_length=20, blank=True, null=True)
    entered_student_name = models.CharField(max_length=150, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=PartStatus.choices,
        default=PartStatus.REGISTERED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    
    # Check-in info
    checkin_time = models.DateTimeField(null=True, blank=True)
    photo_path = models.CharField(max_length=500, blank=True, null=True)
    attendance_session = models.ForeignKey(
        'attendance.AttendanceSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='participations',
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_participations',
    )
    
    # Point info
    awarded_points = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    point_category = models.ForeignKey(
        PointCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_participations',
    )
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_participations',
    )
    awarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'activity_participations'
        verbose_name = 'Tham gia hoạt động'
        verbose_name_plural = 'Tham gia hoạt động'
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'student'],
                condition=models.Q(student__isnull=False),
                name='unique_activity_student_participation',
            )
        ]

    def __str__(self):
        code = self.entered_student_code or (self.student.username if self.student else "Unknown")
        return f"{code} -> {self.activity.title}"
