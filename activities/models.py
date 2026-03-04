from django.conf import settings
from django.db import models


class PointCategory(models.Model):
    """
    Categories for training/activity points.
    Maps to table: point_categories
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'point_categories'
        verbose_name = 'Mục điểm rèn luyện'
        verbose_name_plural = 'Mục điểm rèn luyện'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"



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


class ActivityRegistration(models.Model):
    """
    Student registration for activities.
    Maps to table: activity_registrations
    """

    class RegStatus(models.TextChoices):
        REGISTERED = 'REGISTERED', 'Đã đăng ký'
        CANCELED = 'CANCELED', 'Đã hủy'
        BANNED = 'BANNED', 'Bị cấm'
        ATTENDED = 'ATTENDED', 'Đã tham gia'
        POINT_AWARDED = 'POINT_AWARDED', 'Đã cộng điểm'

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='registrations',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_registrations',
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=RegStatus.choices,
        default=RegStatus.REGISTERED,
    )

    class Meta:
        db_table = 'activity_registrations'
        verbose_name = 'Đăng ký hoạt động'
        verbose_name_plural = 'Đăng ký hoạt động'
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'student'],
                name='unique_activity_registration',
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.activity}"


class Budget(models.Model):
    """
    Budget planning for each activity.
    Maps to table: budgets
    """

    class BudgetStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Nháp'
        APPROVED = 'APPROVED', 'Đã duyệt'
        REJECTED = 'REJECTED', 'Từ chối'

    activity = models.OneToOneField(
        Activity,
        on_delete=models.CASCADE,
        related_name='budget',
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=BudgetStatus.choices,
        default=BudgetStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_budgets',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        verbose_name = 'Ngân sách'
        verbose_name_plural = 'Ngân sách'

    def __str__(self):
        return f"Budget: {self.activity.title}"


class BudgetItem(models.Model):
    """
    Individual line items within a budget.
    Maps to table: budget_items
    """

    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'budget_items'
        verbose_name = 'Khoản mục ngân sách'
        verbose_name_plural = 'Khoản mục ngân sách'

    def __str__(self):
        return f"{self.name} ({self.amount})"


class Task(models.Model):
    """
    Task assignment within an activity's organizing committee.
    Maps to table: tasks
    """

    class TaskStatus(models.TextChoices):
        TODO = 'TODO', 'Chưa làm'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang làm'
        DONE = 'DONE', 'Hoàn thành'

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_tasks',
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        verbose_name = 'Nhiệm vụ'
        verbose_name_plural = 'Nhiệm vụ'

    def __str__(self):
        return self.title
