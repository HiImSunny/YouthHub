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


