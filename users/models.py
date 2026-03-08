from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for YouthHub.
    Maps to table: users
    Roles: ADMIN, STAFF (Can bo Doan-Hoi), STUDENT
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        STAFF = 'STAFF', 'Cán bộ Đoàn-Hội'
        STUDENT = 'STUDENT', 'Sinh viên'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Hoạt động'
        LOCKED = 'LOCKED', 'Bị khóa'

    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    avatar_url = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Django auth fields
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'

    def __str__(self):
        return f"{self.full_name} ({self.username})"


class StudentProfile(models.Model):
    """
    Student academic profile, 1:1 with User (role=STUDENT).
    Maps to table: student_profiles
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    student_code = models.CharField(max_length=20, unique=True)
    course_year = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Hồ sơ sinh viên'
        verbose_name_plural = 'Hồ sơ sinh viên'

    def __str__(self):
        return f"{self.student_code} - {self.user.full_name}"
