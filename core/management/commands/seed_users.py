"""
Management command: seed_users
Creates demo accounts for all 3 roles: ADMIN, STAFF, STUDENT
Also seeds: StudentProfiles, OrganizationMembers, PointCategories, Activities
Run with: python manage.py seed_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed demo users (ADMIN, STAFF, STUDENT) + related data'

    # ── Shared password for all demo accounts ──────────────────────────────────
    DEMO_PASSWORD = 'Admin@123'

    def handle(self, *args, **options):
        self._seed_point_categories()
        self._seed_admin()
        self._seed_staff()
        self._seed_students()
        self._seed_activities()
        self.stdout.write(self.style.SUCCESS(
            '\n[OK] All seed data created! '
            f'Login password for everyone: {self.DEMO_PASSWORD}'
        ))

    # ── 1. Point Categories ────────────────────────────────────────────────────
    def _seed_point_categories(self):
        from activities.models import PointCategory
        cats = [
            ('CAT-A', 'Rèn luyện đạo đức, lối sống'),
            ('CAT-B', 'Học tập và nghiên cứu khoa học'),
            ('CAT-C', 'Hoạt động xã hội, tình nguyện'),
            ('CAT-D', 'Văn hóa, thể thao, nghệ thuật'),
            ('CAT-E', 'Hoạt động Đoàn - Hội'),
        ]
        for code, name in cats:
            obj, created = PointCategory.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True},
            )
            if created:
                self.stdout.write(f'  + PointCategory: {code}')

    # ── 2. Admin ───────────────────────────────────────────────────────────────
    def _seed_admin(self):
        admins = [
            {
                'username': 'admin',
                'email': 'admin@youthhub.edu.vn',
                'full_name': 'Lương Duy Khang',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            },
        ]
        for data in admins:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'full_name': data['full_name'],
                    'role': data['role'],
                    'is_staff': data.get('is_staff', False),
                    'is_superuser': data.get('is_superuser', False),
                    'status': 'ACTIVE',
                }
            )
            if created:
                user.set_password(self.DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  + ADMIN: {user.username}'))
            else:
                self.stdout.write(f'  ~ ADMIN exists: {user.username}')

    # ── 3. Staff (Cán bộ Đoàn - Hội) ─────────────────────────────────────────
    def _seed_staff(self):
        from core.models import Organization, OrganizationMember

        staff_data = [
            {
                'username': 'staff01',
                'email': 'canbo01@youthhub.edu.vn',
                'full_name': 'Trần Thị Hồng Nhung',
                'org_code': 'DT-NCT',
                'position': 'Bí thư',
            },
            {
                'username': 'staff02',
                'email': 'canbo02@youthhub.edu.vn',
                'full_name': 'Lê Văn Minh Hoàng',
                'org_code': 'DK-CNTT',
                'position': 'Phó Bí thư',
            },
            {
                'username': 'staff03',
                'email': 'canbo03@youthhub.edu.vn',
                'full_name': 'Phạm Thị Mỹ Duyên',
                'org_code': 'CLB-CNTT',
                'position': 'Ủy viên Ban Chấp hành',
            },
        ]

        for data in staff_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'full_name': data['full_name'],
                    'role': 'STAFF',
                    'is_staff': True,
                    'status': 'ACTIVE',
                }
            )
            if created:
                user.set_password(self.DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  + STAFF: {user.username}'))

                # Add to organization
                try:
                    org = Organization.objects.get(code=data['org_code'])
                    OrganizationMember.objects.get_or_create(
                        organization=org,
                        user=user,
                        defaults={
                            'position': data['position'],
                            'is_officer': True,
                            'joined_at': date(2025, 9, 1),
                        }
                    )
                except Organization.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f'    ! Org {data["org_code"]} not found. Run seed_data first.'
                    ))
            else:
                self.stdout.write(f'  ~ STAFF exists: {user.username}')

    # ── 4. Students ────────────────────────────────────────────────────────────
    def _seed_students(self):
        from users.models import StudentProfile
        from core.models import Organization, OrganizationMember

        students = [
            {
                'username': 'sv001',
                'email': 'sv001@student.edu.vn',
                'full_name': 'Nguyễn Minh An',
                'student_code': 'NCT2100001',
                'faculty': 'Công nghệ Thông tin',
                'class_name': 'DHCNTT21A',
                'course_year': 'K2021',
                'org_code': 'CLB-CNTT',
            },
            {
                'username': 'sv002',
                'email': 'sv002@student.edu.vn',
                'full_name': 'Trần Thanh Bình',
                'student_code': 'NCT2100002',
                'faculty': 'Công nghệ Thông tin',
                'class_name': 'DHCNTT21A',
                'course_year': 'K2021',
                'org_code': 'CLB-CNTT',
            },
            {
                'username': 'sv003',
                'email': 'sv003@student.edu.vn',
                'full_name': 'Lê Thị Cẩm',
                'student_code': 'NCT2200003',
                'faculty': 'Công nghệ Thông tin',
                'class_name': 'DHCNTT22B',
                'course_year': 'K2022',
                'org_code': 'DK-CNTT',
            },
            {
                'username': 'sv004',
                'email': 'sv004@student.edu.vn',
                'full_name': 'Phạm Hoàng Duy',
                'student_code': 'NCT2200004',
                'faculty': 'Công nghệ Thông tin',
                'class_name': 'DHCNTT22B',
                'course_year': 'K2022',
                'org_code': 'DK-CNTT',
            },
            {
                'username': 'sv005',
                'email': 'sv005@student.edu.vn',
                'full_name': 'Võ Thị Lan',
                'student_code': 'NCT2300005',
                'faculty': 'Kinh tế',
                'class_name': 'DHKT23A',
                'course_year': 'K2023',
                'org_code': 'DT-NCT',
            },
        ]

        for data in students:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'full_name': data['full_name'],
                    'role': 'STUDENT',
                    'status': 'ACTIVE',
                }
            )
            if created:
                user.set_password(self.DEMO_PASSWORD)
                user.save()

                # Student profile
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'student_code': data['student_code'],
                        'faculty': data['faculty'],
                        'class_name': data['class_name'],
                        'course_year': data['course_year'],
                    }
                )

                # Org membership
                try:
                    org = Organization.objects.get(code=data['org_code'])
                    OrganizationMember.objects.get_or_create(
                        organization=org,
                        user=user,
                        defaults={
                            'position': 'Đoàn viên',
                            'is_officer': False,
                            'joined_at': date(2025, 9, 1),
                        }
                    )
                except Organization.DoesNotExist:
                    pass

                self.stdout.write(self.style.SUCCESS(
                    f'  + STUDENT: {user.username}'
                ))
            else:
                self.stdout.write(f'  ~ STUDENT exists: {user.username}')

    # ── 5. Demo Activities ─────────────────────────────────────────────────────
    def _seed_activities(self):
        from activities.models import Activity, PointCategory, ActivityRegistration
        from core.models import Organization, Semester

        try:
            staff = User.objects.get(username='staff01')
            admin = User.objects.get(username='admin')
            org = Organization.objects.get(code='DK-CNTT')
            semester = Semester.objects.filter(is_current=True).first()
            cat = PointCategory.objects.filter(code='CAT-C').first()
        except (User.DoesNotExist, Organization.DoesNotExist):
            self.stdout.write(self.style.WARNING(
                '  ! Skipping activities: required seed data missing.'
            ))
            return

        now = timezone.now()
        activities_data = [
            {
                'code': 'HD-2026-001',
                'title': 'Ngay hoi Cong nghe Xanh 2026',
                'description': 'Su kien thuong nien ket noi sinh vien nganh CNTT.',
                'activity_type': 'ACADEMIC',
                'start_time': now + timedelta(days=7),
                'end_time': now + timedelta(days=7, hours=8),
                'location': 'Hoi truong A - Truong DH Nam Can Tho',
                'status': 'APPROVED',
                'approved_by': admin,
            },
            {
                'code': 'HD-2026-002',
                'title': 'Chien dich Tinh nguyen Mua He Xanh',
                'description': 'Chien dich tinh nguyen giup do ba con vung nong thon Can Tho.',
                'activity_type': 'VOLUNTEER',
                'start_time': now + timedelta(days=30),
                'end_time': now + timedelta(days=35),
                'location': 'Huyen Phong Dien, Can Tho',
                'status': 'PENDING',
                'approved_by': None,
            },
            {
                'code': 'HD-2026-003',
                'title': 'Sinh hoat Chi doan Thang 3',
                'description': 'Sinh hoat dinh ky Chi doan — kiem diem hoat dong va len ke hoach thang moi.',
                'activity_type': 'MEETING',
                'start_time': now - timedelta(days=3),
                'end_time': now - timedelta(days=3) + timedelta(hours=2),
                'location': 'Phong E201',
                'status': 'DONE',
                'approved_by': admin,
            },
            {
                'code': 'HD-2026-004',
                'title': 'Cuoc thi Lap trinh ACM/ICPC',
                'description': 'Vong so loai cuoc thi lap trinh quoc te ACM/ICPC cap truong.',
                'activity_type': 'ACADEMIC',
                'start_time': now + timedelta(days=14),
                'end_time': now + timedelta(days=14, hours=5),
                'location': 'Phong may B102',
                'status': 'DRAFT',
                'approved_by': None,
            },
        ]

        students = User.objects.filter(role='STUDENT')

        for data in activities_data:
            act, created = Activity.objects.get_or_create(
                code=data['code'],
                defaults={
                    'organization': org,
                    'semester': semester,
                    'point_category': cat,
                    'title': data['title'],
                    'description': data['description'],
                    'activity_type': data['activity_type'],
                    'start_time': data['start_time'],
                    'end_time': data['end_time'],
                    'location': data['location'],
                    'status': data['status'],
                    'created_by': staff,
                    'approved_by': data['approved_by'],
                    'approved_at': timezone.now() if data['approved_by'] else None,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  + Activity [{data["status"]}]: {data["code"]}'))
                # Register students for APPROVED activity
                if act.status == 'APPROVED':
                    for sv in students[:3]:
                        ActivityRegistration.objects.get_or_create(
                            activity=act,
                            student=sv,
                            defaults={'status': 'REGISTERED'},
                        )
                    self.stdout.write(f'    -> Registered {min(3, students.count())} students')
            else:
                self.stdout.write(f'  ~ Activity exists: {data["code"]}')
