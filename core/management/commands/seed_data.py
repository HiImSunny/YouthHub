from django.core.management.base import BaseCommand
from core.models import Organization, Semester
from datetime import date


class Command(BaseCommand):
    help = 'Seed initial data: semesters and organizations'

    def handle(self, *args, **options):
        # 1. Create organizations (hierarchical)
        doan_truong, created = Organization.objects.get_or_create(
            code='DT-NCT',
            defaults={
                'parent': None,
                'type': Organization.OrgType.UNION_SCHOOL,
                'name': 'Đoàn trường Đại học Nam Cần Thơ',
                'description': 'Đoàn TNCS Cần Thơ - Trường Đại học Nam Cần Thơ',
                'status': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created org: {doan_truong}'))

        doan_khoa, created = Organization.objects.get_or_create(
            code='DK-CNTT',
            defaults={
                'parent': doan_truong,
                'type': Organization.OrgType.UNION_FACULTY,
                'name': 'Đoàn khoa Công nghệ Thông tin',
                'description': 'Liên chi Đoàn khoa CNTT',
                'status': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created org: {doan_khoa}'))

        clb, created = Organization.objects.get_or_create(
            code='CLB-CNTT',
            defaults={
                'parent': doan_khoa,
                'type': Organization.OrgType.CLUB,
                'name': 'CLB Công nghệ Thông tin',
                'description': 'Câu lạc bộ CNTT thuộc Đoàn khoa CNTT',
                'status': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created org: {clb}'))

        # 2. Create semesters
        s1, created = Semester.objects.get_or_create(
            name='Học kỳ 1',
            academic_year='2025-2026',
            organization=doan_truong,
            defaults={
                'start_date': date(2025, 9, 1),
                'end_date': date(2026, 1, 15),
                'is_current': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created semester: {s1}'))

        s2, created = Semester.objects.get_or_create(
            name='Học kỳ 2',
            academic_year='2025-2026',
            organization=doan_truong,
            defaults={
                'start_date': date(2026, 2, 1),
                'end_date': date(2026, 6, 30),
                'is_current': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created semester: {s2}'))

        self.stdout.write(self.style.SUCCESS('[OK] Seed data completed!'))
