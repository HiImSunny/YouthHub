from django.conf import settings
from django.db import models


class AttendanceSession(models.Model):
    """
    A check-in session within an activity (e.g. Opening, Closing).
    Maps to table: attendance_sessions
    Generates QR token for web-based check-in form.
    """

    class SessionStatus(models.TextChoices):
        OPEN = 'OPEN', 'Đang mở'
        CLOSED = 'CLOSED', 'Đã đóng'

    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
    )
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    qr_token = models.CharField(max_length=255, unique=True)
    requires_photo = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=SessionStatus.choices,
        default=SessionStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_sessions'
        verbose_name = 'Phiên điểm danh'
        verbose_name_plural = 'Phiên điểm danh'

    def __str__(self):
        return f"{self.activity.title} - {self.name}"


class AttendanceRecord(models.Model):
    """
    Individual check-in record for a student in a session.
    Maps to table: attendance_records
    student_id is nullable to support guests who are not logged in.
    NOTE: Activity is accessed via attendance_session.activity (no direct FK to avoid redundancy).
    """

    class RecordStatus(models.TextChoices):
        PENDING = 'PENDING', 'Chờ xác nhận'
        VERIFIED = 'VERIFIED', 'Đã xác nhận'
        REJECTED = 'REJECTED', 'Từ chối'

    attendance_session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
    )
    entered_student_code = models.CharField(max_length=20)
    entered_student_name = models.CharField(max_length=150, blank=True, null=True)
    checkin_time = models.DateTimeField(auto_now_add=True)
    photo_path = models.CharField(max_length=500, blank=True, null=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_records',
    )
    status = models.CharField(
        max_length=20,
        choices=RecordStatus.choices,
        default=RecordStatus.PENDING,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'attendance_records'
        verbose_name = 'Bản ghi điểm danh'
        verbose_name_plural = 'Bản ghi điểm danh'
        constraints = [
            models.UniqueConstraint(
                fields=['attendance_session', 'student'],
                condition=models.Q(student__isnull=False),
                name='unique_session_student',
            )
        ]

    def __str__(self):
        return f"{self.entered_student_code} @ {self.attendance_session}"

    @property
    def activity(self):
        """Convenience property — access activity via session (no direct FK)."""
        return self.attendance_session.activity


class ActivityPoint(models.Model):
    """
    Activity points earned by students after being approved.
    Maps to table: activity_points
    - point_category: snapshot of activity's category at award time
    - awarded_by: who granted the points (audit trail)
    - awarded_at: when points were granted
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_points',
    )
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.CASCADE,
        related_name='awarded_activity_points',
    )
    point_category = models.ForeignKey(
        'activities.PointCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_points',
        help_text='Snapshot danh mục điểm tại thời điểm cấp — không thay đổi dù Activity bị sửa',
    )
    points = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True, default='')
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_points',
        help_text='Cán bộ đã duyệt và cấp điểm',
    )
    awarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_points'
        verbose_name = 'Điểm hoạt động'
        verbose_name_plural = 'Điểm hoạt động'
        constraints = [
            # Each student can only receive points once per activity
            models.UniqueConstraint(
                fields=['student', 'activity'],
                name='unique_student_activity_point',
            )
        ]

    def __str__(self):
        return f"{self.student} +{self.points} ({self.activity.title})"
